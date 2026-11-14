"""API contract tests: every field the web app reads must exist.

This is the guard against a green build with blank panels.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from rootshift.api.app import app

client = TestClient(app)


def _wait_job(job_id: str, timeout: float = 120.0) -> dict:
    started = time.time()
    while time.time() - started < timeout:
        payload = client.get(f"/api/v1/jobs/{job_id}").json()
        data = payload["data"]
        if data["status"] == "done":
            return data["result"]
        if data["status"] == "failed":
            raise AssertionError(data.get("error"))
        time.sleep(0.2)
    raise AssertionError("job timeout")


@pytest.fixture(scope="module")
def farm():
    res = client.post("/api/v1/farms", json={"demo_farm_id": "demo_finney"})
    assert res.status_code == 201, res.text
    return res.json()["data"]


def test_meta_endpoints():
    region = client.get("/api/v1/meta/region").json()["data"]
    assert region["id"] == "us_ks"
    assert len(region["demo_farms"]) == 3
    sources = client.get("/api/v1/meta/sources").json()["data"]
    assert len(sources["products"]) == 23
    crops = client.get("/api/v1/catalog/crops").json()["data"]
    assert len(crops) == 9
    assert all(c["name_es"] for c in crops), "the design panel needs a Spanish name per crop"


def test_farm_creation_payload(farm):
    for key in ("farm_id", "name", "area_ha", "county", "confidence", "caveats", "build_ms",
                "boundary", "location", "irrigation"):
        assert key in farm, key
    assert farm["area_ha"] > 0
    assert len(farm["boundary"]) >= 4


def test_context_contract(farm):
    data = client.get(f"/api/v1/farms/{farm['farm_id']}/context").json()["data"]
    assert set(["climate", "soil", "drought", "water", "carbon", "erosion", "confidence"]) <= set(data)
    assert {"p10", "p50", "p90"} <= set(data["climate"]["annual_precip"])
    assert {"spei3", "spei12", "spei3_class", "add_days"} <= set(data["drought"])
    assert {"texture_class", "hydgrp", "theta_fc", "theta_wp", "k_factor"} <= set(data["soil"])
    assert data["provenance"], "provenance must never be empty"


def test_rotation_contract(farm):
    res = client.post(f"/api/v1/farms/{farm['farm_id']}/rotation:optimize", json={})
    assert res.status_code == 202
    result = _wait_job(res.json()["data"]["job_id"])["result"]

    metrics = result["metrics"]
    for key in ("production_index", "p10_index", "p50_index", "p90_index", "cv",
                "p_fail", "recovery_years", "p_drought3", "yield_mean_t_ha"):
        assert key in metrics, key

    assert {"production_pct", "p_fail_delta", "irs_delta"} <= set(result["delta"])
    irs = result["irs"]
    assert 0 <= irs["value"] <= 100
    assert set(irs["components"]) == {"water", "stability", "soil", "diversity", "health", "hazard"}
    assert set(irs["weights"]) == set(irs["components"])

    sequence = result["sequence"]
    assert len(sequence) == 8
    for item in sequence:
        assert {"k", "season", "crop_id", "crop_name", "family", "area_ha"} <= set(item)

    assert len(result["findings"]) >= 3
    for finding in result["findings"]:
        assert {"code", "severity", "text", "evidence"} <= set(finding)

    assert set(["S0", "S1", "S2", "S6", "S7"]) <= set(result["scenarios"])
    assert result["baseline"]["metrics"]["production_index"] > 0

    nut = result["nutrients"]
    for key in ("n_removal_kg_ha", "n_fixation_kg_ha", "n_balance_kg_ha",
                "p2o5_balance_kg_ha", "k2o_balance_kg_ha", "n_status", "inputs_declared"):
        assert key in nut, key


def test_disease_contract(farm):
    data = client.get(f"/api/v1/farms/{farm['farm_id']}/diseases").json()["data"]
    assert data["crops"]
    crop = data["crops"][0]
    assert crop["diseases"]
    disease = crop["diseases"][0]
    for key in ("disease_id", "name", "pathogen", "risk_index", "level", "actions"):
        assert key in disease, key
    assert 0 <= disease["risk_index"] <= 100
    assert disease["level"] in ("low", "medium", "high", "very high")


def test_hazards_contract(farm):
    data = client.get(f"/api/v1/farms/{farm['farm_id']}/hazards").json()["data"]
    assert len(data["hazards"]) == 8
    calculable = [h for h in data["hazards"] if h["calculable"]]
    assert len(calculable) == 6
    for hazard in data["hazards"]:
        assert {"hazard", "name", "calculable", "playbook", "source"} <= set(hazard)
        assert set(hazard["playbook"]) == {"before", "during", "after"}
    assert "windows" in data["workability"]
    assert {"spei3", "add_days"} <= set(data["current"])


def test_irrigation_contract(farm):
    data = client.post(f"/api/v1/farms/{farm['farm_id']}/irrigation", json={}).json()["data"]
    assert data["system"]["id"] in ("center_pivot", "pivot_lepa", "sdi", "furrow", "micro", "rainfed")
    assert data["parcel"]["boundary"]
    if data["system"]["id"] != "rainfed":
        assert data["design_flow_l_s"] > 0
        assert data["zones"]
        assert len(data["schedule"]["etc_mm"]) == 12
        assert data["materials"]


def test_timeline_contract(farm):
    data = client.get(f"/api/v1/farms/{farm['farm_id']}/timeline?layer=ndvi").json()["data"]
    assert data["points"]
    point = data["points"][0]
    assert {"t", "mean", "min", "max"} <= set(point)
    assert data["available_range"]["from"] <= data["available_range"]["to"]


def test_unknown_farm_is_404():
    res = client.get("/api/v1/farms/frm_missing/context")
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_health():
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["data_mode"] == "demo"
