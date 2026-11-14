"""Farms created from a polygon drawn on the map."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from rootshift import config
from rootshift.api.app import app
from rootshift.services import fixture_builder

client = TestClient(app)


def _square(lat: float, lon: float, side_m: float) -> list[list[float]]:
    dlat = side_m / 2 / 111_320.0
    dlon = side_m / 2 / (111_320.0 * 0.788)  # cos(38 deg)
    ring = [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
        [lon - dlon, lat - dlat],
    ]
    return ring


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def test_ring_is_closed_and_rounded():
    ring = fixture_builder.normalise_ring(
        [[-100.1234567, 38.7654321], [-100.12, 38.77], [-100.11, 38.78]]
    )
    assert ring[0] == ring[-1]
    assert ring[0] == [-100.123457, 38.765432]


def test_ring_rejects_too_few_points():
    with pytest.raises(ValueError) as err:
        fixture_builder.normalise_ring([[1.0, 2.0], [1.1, 2.1]])
    assert "POLYGON_TOO_SMALL" in str(err.value)


def test_ring_rejects_collinear_points():
    with pytest.raises(ValueError):
        fixture_builder.normalise_ring([[1.0, 2.0], [1.1, 2.0], [1.2, 2.0]])


def test_ring_rejects_locations_outside_the_pilot():
    ring = _square(48.85, 2.35, 800)  # Paris
    with pytest.raises(ValueError) as err:
        fixture_builder.normalise_ring(ring)
    assert "LOCATION_OUT_OF_US" in str(err.value)


def test_ring_rejects_absurd_areas():
    with pytest.raises(ValueError) as err:
        fixture_builder.normalise_ring(_square(38.0, -100.0, 40_000))  # 400 km across
    assert "POLYGON_TOO_LARGE" in str(err.value)


def test_area_and_centroid_of_a_one_km_square():
    ring = _square(38.05, -100.92, 1000)
    area = fixture_builder.polygon_area_ha(ring)
    assert 95 < area < 105, area  # ~100 ha
    lat, lon = fixture_builder.polygon_centroid(ring)
    assert lat == pytest.approx(38.05, abs=1e-4)
    assert lon == pytest.approx(-100.92, abs=1e-4)


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

@pytest.fixture()
def fake_builder(monkeypatch):
    """Build a fixture from the demo one instead of calling POWER/SSURGO."""
    calls = {}

    def fake(lat, lon, area_ha, name, **kwargs):
        calls.update({"lat": lat, "lon": lon, "area_ha": area_ha, "ring": kwargs.get("ring")})
        fixture = json.loads((config.FIXTURES_DIR / "demo_finney.json").read_text(encoding="utf-8"))
        fixture["farm"]["id"] = "custom_polygon_test"
        fixture["farm"]["name"] = name or "Drawn paddock"
        fixture["farm"]["boundary"] = kwargs.get("ring")
        fixture["farm"]["area_ha"] = round(area_ha, 1)
        fixture["farm"]["location"] = {"lat": lat, "lon": lon}
        return fixture

    monkeypatch.setattr("rootshift.api.app.fixture_builder.build_custom_fixture", fake)
    return calls


def test_create_farm_from_drawn_polygon(fake_builder):
    ring = _square(38.05, -100.92, 900)
    res = client.post("/api/v1/farms", json={"name": "South paddock", "boundary": ring})
    assert res.status_code == 201, res.text
    data = res.json()["data"]

    assert data["area_ha"] == pytest.approx(81, abs=12)
    assert len(data["boundary"]) == len(ring)
    assert data["boundary"][0][0] == pytest.approx(ring[0][0], abs=1e-6)
    assert data["boundary"][0][1] == pytest.approx(ring[0][1], abs=1e-6)
    assert data["county"] == "Finney"
    # the drawn ring reached the builder, not a generated square
    assert fake_builder["ring"] is not None
    assert fake_builder["ring"][0] == pytest.approx([ring[0][0], ring[0][1]], abs=1e-6)


def test_create_farm_from_polygon_returns_it_in_the_context(fake_builder):
    ring = _square(38.05, -100.92, 700)
    farm = client.post("/api/v1/farms", json={"boundary": ring}).json()["data"]
    ctx = client.get(f"/api/v1/farms/{farm['farm_id']}/context").json()["data"]
    assert "boundary" in ctx["farm"]
    assert len(ctx["farm"]["boundary"]) == len(ring)


def test_create_farm_without_polygon_or_coordinates_is_rejected():
    res = client.post("/api/v1/farms", json={"name": "nowhere"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_farm_rejects_out_of_range_polygon():
    res = client.post("/api/v1/farms", json={"boundary": [[181, 10], [182, 10], [182, 11]]})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "POLYGON_INVALID"


def test_polygon_takes_precedence_over_lat_lon(fake_builder):
    ring = _square(38.4, -101.0, 800)
    res = client.post(
        "/api/v1/farms",
        json={"boundary": ring, "latitude": 39.0, "longitude": -98.0, "area_ha": 10},
    )
    assert res.status_code == 201
    # centroid of the polygon wins over the stray latitude/longitude fields
    assert fake_builder["lat"] == pytest.approx(38.4, abs=1e-3)
    assert fake_builder["lon"] == pytest.approx(-101.0, abs=1e-3)
