"""Manual rotation editing (spec 13.3: edit and see the metrics recomputed)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from rootshift.api.app import app

client = TestClient(app)


def _wait(job_id: str) -> dict:
    for _ in range(200):
        payload = client.get(f"/api/v1/jobs/{job_id}").json()["data"]
        if payload["status"] in ("done", "failed"):
            assert payload["status"] == "done", payload.get("error")
            return payload["result"]["result"]
        time.sleep(0.2)
    raise AssertionError("job timeout")


@pytest.fixture(scope="module")
def rotation():
    res = client.post("/api/v1/farms", json={"demo_farm_id": "demo_finney"})
    farm_id = res.json()["data"]["farm_id"]
    job = client.post(f"/api/v1/farms/{farm_id}/rotation:optimize", json={}).json()["data"]["job_id"]
    result = _wait(job)
    return farm_id, result


def _ids(rotation_result):
    return [item["crop_id"] for item in rotation_result["sequence"]]


def test_edit_recomputes_metrics_and_irs(rotation):
    farm_id, optimized = rotation
    ids = _ids(optimized)
    # swap season 1 for a crop that is not the current one
    replacement = next(c for c in ("corn", "soybean", "wheat") if c != ids[0] and c in ("corn", "soybean", "winter_wheat"))
    ids[0] = replacement

    res = client.put(f"/api/v1/farms/{farm_id}/rotations/{optimized['rotation_id']}", json={"sequence": ids})
    assert res.status_code == 200, res.text
    body = res.json()["data"]

    assert body["edited"] is True
    assert body["sequence"][0]["crop_id"] == replacement
    assert len(body["sequence"]) == len(ids)
    assert "irs" in body and 0 <= body["irs"]["value"] <= 100
    assert "nutrients" in body
    assert "findings" in body
    assert "delta" in body
    # the baseline must still be the optimised one, not the edit
    assert body["baseline"]["metrics"] == optimized["baseline"]["metrics"]


def test_edit_is_reproducible(rotation):
    farm_id, optimized = rotation
    ids = _ids(optimized)
    first = client.put(f"/api/v1/farms/{farm_id}/rotations/{optimized['rotation_id']}", json={"sequence": ids}).json()["data"]
    second = client.put(f"/api/v1/farms/{farm_id}/rotations/{optimized['rotation_id']}", json={"sequence": ids}).json()["data"]
    assert first["metrics"] == second["metrics"]
    assert first["irs"]["value"] == second["irs"]["value"]


def test_edit_flags_family_repetition(rotation):
    farm_id, optimized = rotation
    ids = _ids(optimized)
    ids[0] = "corn"
    ids[1] = "grain_sorghum"  # same family (poaceae)
    body = client.put(f"/api/v1/farms/{farm_id}/rotations/{optimized['rotation_id']}", json={"sequence": ids}).json()["data"]
    codes = [w["code"] for w in body["warnings"]]
    assert "R2" in codes
    assert any("familia" in w["message_es"] for w in body["warnings"])


def test_edit_flags_repeated_species(rotation):
    farm_id, optimized = rotation
    ids = _ids(optimized)
    ids[0] = "corn"
    ids[1] = "corn"
    body = client.put(f"/api/v1/farms/{farm_id}/rotations/{optimized['rotation_id']}", json={"sequence": ids}).json()["data"]
    assert "R3" in [w["code"] for w in body["warnings"]]


def test_edit_rejects_wrong_length(rotation):
    farm_id, optimized = rotation
    res = client.put(f"/api/v1/farms/{farm_id}/rotations/{optimized['rotation_id']}", json={"sequence": ["corn"]})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_edit_rejects_unknown_crop(rotation):
    farm_id, optimized = rotation
    ids = _ids(optimized)
    ids[0] = "banana"
    res = client.put(f"/api/v1/farms/{farm_id}/rotations/{optimized['rotation_id']}", json={"sequence": ids})
    assert res.status_code == 400


def test_edit_requires_existing_rotation(rotation):
    farm_id, _ = rotation
    res = client.put(f"/api/v1/farms/{farm_id}/rotations/rot_missing", json={"sequence": ["corn"] * 8})
    assert res.status_code == 404


def test_context_exposes_the_crop_catalog(rotation):
    farm_id, _ = rotation
    body = client.get(f"/api/v1/farms/{farm_id}/context").json()["data"]
    assert len(body["crops"]) == 9
    sample = body["crops"][0]
    assert {"crop_id", "name_en", "name_es", "family"} <= set(sample)
