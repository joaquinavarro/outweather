"""Custom-field pipeline: geometry, county resolution and fixture building.

Network is mocked so these run offline and fast.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pytest

from rootshift.services import fixture_builder as fb


def test_polygon_from_center_area_is_close_to_requested():
    ring, area = fb.polygon_from_center(38.84, -97.61, 65.0)
    assert area == 65.0
    measured = fb.polygon_area_ha(ring)
    assert 58.0 <= measured <= 72.0, measured


def test_polygon_is_closed():
    ring, _ = fb.polygon_from_center(38.0, -100.0, 10.0)
    assert ring[0] == ring[-1]
    assert len(ring) == 5


def test_resolve_county_uses_nominatim_and_index(monkeypatch):
    def fake_json(url, payload=None, timeout=60, retries=3):
        assert "nominatim" in url
        return {
            "address": {"county": "Saline County", "state": "Kansas", "state_code": "KS"}
        }

    monkeypatch.setattr(fb.provider_base, "http_json", fake_json)
    entry = fb.resolve_county(38.84, -97.61)
    assert entry["areasymbol"] == "KS169"
    assert entry["county"] == "Saline"


def test_resolve_county_rejects_outside_us():
    with pytest.raises(ValueError, match="LOCATION_OUT_OF_US"):
        fb.resolve_county(51.5, -0.1)


def _fake_weather(lat: float) -> dict:
    days = 365 * 3
    start = dt.date(2022, 1, 1)
    dates = [(start + dt.timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]
    rng = np.random.default_rng(0)
    doy = np.array([(start + dt.timedelta(days=i)).timetuple().tm_yday for i in range(days)])
    tmax = 18 + 14 * np.sin(2 * np.pi * (doy - 100) / 365) + rng.normal(0, 2, days)
    tmin = tmax - 12
    tdew = tmin - 1
    return {
        "dates": dates,
        "tmax": [round(float(v), 2) for v in tmax],
        "tmin": [round(float(v), 2) for v in tmin],
        "tdew": [round(float(v), 2) for v in tdew],
        "rh": [65.0] * days,
        "ws": [3.5] * days,
        "rs": [20.0] * days,
        "ps": [92.0] * days,
        "pr": [round(float(max(0.0, rng.normal(1.5, 3))), 2) for _ in range(days)],
        "et0": [round(float(max(0.2, 3 + rng.normal(0, 0.6))), 2) for _ in range(days)],
        "cell": {"lat": lat, "lon": -97.61, "elevation_m": 380.0},
    }


def test_build_custom_fixture_offline(monkeypatch):
    monkeypatch.setattr(fb, "resolve_county", lambda lat, lon: {
        "areasymbol": "KS169", "state": "Kansas", "state_code": "KS", "county": "Saline"
    })
    monkeypatch.setattr(fb.power_provider, "fetch_daily", lambda *a, **k: _fake_weather(38.84))
    monkeypatch.setattr(fb.soil_provider, "fetch_soil", lambda *a, **k: fb.soil_provider.default_soil())

    fixture = fb.build_custom_fixture(38.84, -97.61, 40.0, "Test field", "irrigated", "center_pivot", "corn", use_cache=False)

    assert fixture["farm"]["county"] == "Saline"
    assert fixture["farm"]["area_ha"] == 40.0
    assert fixture["farm"]["irrigation"]["status"] == "irrigated"
    assert len(fixture["weather"]["dates"]) == len(fixture["synthetic"]["sm_rz"])
    assert fixture["soil"]["source"] == "default"
    assert fixture["gaez"]["corn"]["rcp45"]["yield_multiplier"] > 0
    assert fixture["meta"]["real_products"][0].startswith("NASA POWER")
