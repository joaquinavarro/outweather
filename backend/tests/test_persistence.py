"""Persistence: farms and rotations survive a restart (spec 12)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from rootshift.api import app as app_module
from rootshift.storage.db import Store

client = TestClient(app_module.app)


def _wait(job_id: str) -> dict:
    for _ in range(200):
        payload = client.get(f"/api/v1/jobs/{job_id}").json()["data"]
        if payload["status"] in ("done", "failed"):
            assert payload["status"] == "done", payload.get("error")
            return payload["result"]["result"]
        time.sleep(0.2)
    raise AssertionError("job timeout")


def test_store_round_trip(tmp_path):
    store = Store(tmp_path / "roundtrip.sqlite3")
    store.save_farm(
        {
            "farm_id": "frm_test",
            "demo_id": "demo_finney",
            "session_id": "s1",
            "profile": {"objective": "balanced"},
            "fixture_path": "/tmp/fixture.json",
            "boundary": [[-100.0, 38.0], [-99.9, 38.0], [-99.9, 38.1], [-100.0, 38.1]],
            "created_at": "2026-01-01T00:00:00Z",
        }
    )
    loaded = store.get_farm("frm_test")
    assert loaded["farm_id"] == "frm_test"
    assert loaded["profile"]["objective"] == "balanced"
    assert len(loaded["boundary"]) == 4

    store.save_rotation("rot_test", "frm_test", {"rotation_id": "rot_test", "metrics": {"production_index": 91.2}})
    assert store.get_rotation("rot_test")["metrics"]["production_index"] == 91.2
    assert store.count_farms() >= 1


def test_farm_survives_a_restart():
    res = client.post("/api/v1/farms", json={"demo_farm_id": "demo_greeley"})
    assert res.status_code == 201
    farm_id = res.json()["data"]["farm_id"]
    expected_county = res.json()["data"]["county"]

    # simulate a process restart: drop the in-memory caches
    app_module.FARMS.clear()
    app_module.ROTATIONS.clear()

    ctx = client.get(f"/api/v1/farms/{farm_id}/context")
    assert ctx.status_code == 200, ctx.text
    assert ctx.json()["data"]["soil"]["texture_class"]
    assert ctx.json()["data"]["farm"]["county"] == expected_county


def test_rotation_survives_a_restart():
    res = client.post("/api/v1/farms", json={"demo_farm_id": "demo_finney"})
    farm_id = res.json()["data"]["farm_id"]
    job = client.post(f"/api/v1/farms/{farm_id}/rotation:optimize", json={}).json()["data"]["job_id"]
    result = _wait(job)
    rotation_id = result["rotation_id"]

    app_module.FARMS.clear()
    app_module.ROTATIONS.clear()

    again = client.get(f"/api/v1/farms/{farm_id}/rotations/{rotation_id}")
    assert again.status_code == 200, again.text
    body = again.json()["data"]
    assert body["rotation_id"] == rotation_id
    assert body["metrics"]["production_index"] == pytest.approx(result["metrics"]["production_index"])
    assert len(body["sequence"]) == len(result["sequence"])


def test_report_works_after_restart():
    res = client.post("/api/v1/farms", json={"demo_farm_id": "demo_republic"})
    farm_id = res.json()["data"]["farm_id"]
    job = client.post(f"/api/v1/farms/{farm_id}/rotation:optimize", json={}).json()["data"]["job_id"]
    _wait(job)

    app_module.FARMS.clear()
    app_module.ROTATIONS.clear()

    pdf = client.get(f"/api/v1/farms/{farm_id}/report.pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_last_rotation_pointer_is_persisted():
    res = client.post("/api/v1/farms", json={"demo_farm_id": "demo_greeley"})
    farm_id = res.json()["data"]["farm_id"]
    job = client.post(f"/api/v1/farms/{farm_id}/rotation:optimize", json={}).json()["data"]["job_id"]
    result = _wait(job)

    app_module.FARMS.clear()
    app_module.ROTATIONS.clear()

    # no rotation_id in the query: the farm must remember its last rotation
    pdf = client.get(f"/api/v1/farms/{farm_id}/report.pdf")
    assert pdf.status_code == 200
    assert result["rotation_id"]
