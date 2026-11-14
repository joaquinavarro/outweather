"""Real GPM IMERG precipitation (P04) wired into the context."""

from __future__ import annotations

import json

import numpy as np
import pytest

from rootshift import config
from rootshift.providers import earthdata
from rootshift.services import context as context_service


def _fixture(demo_id: str) -> dict:
    return json.loads((config.FIXTURES_DIR / f"{demo_id}.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------

def test_parse_ascii_rows():
    payload = (
        "Dataset: file.HDF5\n"
        "precipitation[0][0], 0.1, 0.2, 0.3\n"
        "precipitation[0][1], 0.4, 0.5, 0.6\n"
    )
    parsed = earthdata.parse_ascii(payload)
    assert len(parsed["precipitation"]) == 2
    assert parsed["precipitation"][0] == [0.1, 0.2, 0.3]
    assert parsed["precipitation"][1][2] == pytest.approx(0.6)


def test_parse_ascii_handles_nan():
    parsed = earthdata.parse_ascii("precipitation[0][0], nan, 1.5\n")
    assert np.isnan(parsed["precipitation"][0][0])
    assert parsed["precipitation"][0][1] == pytest.approx(1.5)


def test_grid_index_matches_imerg_grid():
    # IMERG grid starts at -89.95 lat and -179.95 lon, 0.1 degree step
    from pipeline.ingest_imerg import grid_index

    assert grid_index(38.05, -100.92) == (1280, 790)
    assert grid_index(-89.95, -179.95) == (0, 0)


# --------------------------------------------------------------------------
# context integration
# --------------------------------------------------------------------------

@pytest.fixture()
def imerg_payload():
    months = ["2001-01", "2001-02", "2001-03"]
    return {
        "months": months,
        "farms": {
            "demo_finney": {
                "lat": 38.05,
                "lon": -100.92,
                "indices": [1280, 790],
                "mm": [10.0, 20.0, 30.0],
            }
        },
    }


def test_imerg_series_reads_the_cache(monkeypatch, imerg_payload):
    monkeypatch.setattr(context_service, "_imerg_payload", lambda: imerg_payload)
    series = context_service.imerg_series("demo_finney")
    assert series == {"2001-01": 10.0, "2001-02": 20.0, "2001-03": 30.0}
    assert context_service.imerg_series("demo_unknown") is None


def test_imerg_series_rejects_sparse_data(monkeypatch):
    payload = {"months": ["2001-01", "2001-02", "2001-03"], "farms": {"demo_finney": {"mm": [1.0, None, None]}}}
    monkeypatch.setattr(context_service, "_imerg_payload", lambda: payload)
    assert context_service.imerg_series("demo_finney") is None


def test_context_uses_imerg_when_available(monkeypatch):
    months = [f"{y}-{m:02d}" for y in range(2001, 2025) for m in range(1, 13)]
    # a realistic seasonal cycle instead of a constant series (a constant series
    # makes the gamma fit degenerate)
    mm = [40.0 + 30.0 * np.sin(2 * np.pi * (int(m[5:]) - 4) / 12) for m in months]
    payload = {
        "months": months,
        "farms": {"demo_finney": {"lat": 38.05, "lon": -100.92, "indices": [1280, 790], "mm": mm}},
    }
    monkeypatch.setattr(context_service, "_imerg_payload", lambda: payload)
    context_service.CACHE.clear()

    ctx = context_service.build_context(_fixture("demo_finney"), {"objective": "balanced"})
    assert ctx["pr_source"] == "imerg"
    assert "PRECIP_MIXED" in ctx["caveat_codes"]

    # the first simulated months must carry the ingested values, not POWER's
    first_months = list(zip(ctx["monthly"]["year"][:3], ctx["monthly"]["month"][:3], ctx["monthly"]["pr"][:3]))
    for year, month, value in first_months:
        expected = mm[months.index(f"{int(year)}-{int(month):02d}")]
        assert value == pytest.approx(expected, abs=0.01)

    provenance = context_service.provenance_for(ctx)
    assert any(p["product_id"] == "P04" and "IMERG" in p.get("product", "") for p in provenance)


def test_context_falls_back_to_power(monkeypatch):
    monkeypatch.setattr(context_service, "_imerg_payload", lambda: None)
    context_service.CACHE.clear()
    ctx = context_service.build_context(_fixture("demo_greeley"), {"objective": "balanced"})
    assert ctx["pr_source"] == "power"
    assert "PRECIP_MIXED" not in ctx["caveat_codes"]
    assert not any(p["product_id"] == "P04" for p in context_service.provenance_for(ctx))


def test_real_imerg_cache_is_consistent():
    """If the committed precompute exists, it must cover the simulation window."""
    payload = context_service._imerg_payload()
    if not payload:
        pytest.skip("no IMERG precompute in this checkout")
    assert payload["product"] == "GPM_3IMERGM"
    assert len(payload["months"]) >= 200
    for farm in payload["farms"].values():
        assert len(farm["mm"]) == len(payload["months"])
        valid = [v for v in farm["mm"] if v is not None]
        assert len(valid) >= 0.8 * len(payload["months"])
        # Kansas annual precipitation must be in a plausible range
        mean_month = sum(valid) / len(valid)
        assert 20 <= mean_month <= 120
