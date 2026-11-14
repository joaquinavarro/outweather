"""PDF and CSV reports (spec 3.1, 13.3)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from rootshift.api.app import app

client = TestClient(app)


def _wait(job_id: str) -> None:
    for _ in range(200):
        payload = client.get(f"/api/v1/jobs/{job_id}").json()["data"]
        if payload["status"] in ("done", "failed"):
            assert payload["status"] == "done", payload.get("error")
            return
        time.sleep(0.2)
    raise AssertionError("job timeout")


@pytest.fixture(scope="module")
def farm_with_rotation():
    res = client.post("/api/v1/farms", json={"demo_farm_id": "demo_finney"})
    assert res.status_code == 201
    farm_id = res.json()["data"]["farm_id"]
    job = client.post(f"/api/v1/farms/{farm_id}/rotation:optimize", json={}).json()["data"]["job_id"]
    _wait(job)
    return farm_id


def test_pdf_report(farm_with_rotation):
    res = client.get(f"/api/v1/farms/{farm_with_rotation}/report.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment" in res.headers["content-disposition"]
    assert res.headers["content-disposition"].endswith('.pdf"')
    assert res.content.startswith(b"%PDF")
    assert len(res.content) > 3000
    # page compression is off so the text stays extractable
    assert b"ROOTSHIFT" in res.content
    assert b"Field report" in res.content


def test_pdf_report_in_spanish(farm_with_rotation):
    res = client.get(f"/api/v1/farms/{farm_with_rotation}/report.pdf?locale=es-ES")
    assert res.status_code == 200
    assert res.headers["content-language"] == "es-ES"
    assert b"Informe de parcela" in res.content
    assert b"Rotaci" in res.content  # "Rotación propuesta"


def test_csv_report(farm_with_rotation):
    res = client.get(f"/api/v1/farms/{farm_with_rotation}/report.csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    body = res.content.decode("utf-8-sig")
    assert body.startswith("# farm")
    assert "# rotation" in body
    assert "# scenarios" in body
    assert "# nutrients" in body
    assert "# findings" in body
    assert "S0" in body


def test_csv_report_in_spanish(farm_with_rotation):
    res = client.get(f"/api/v1/farms/{farm_with_rotation}/report.csv?locale=es-ES")
    body = res.content.decode("utf-8-sig")
    assert "Campaña" in body
    assert "Cultivo" in body


def test_csv_has_one_row_per_season(farm_with_rotation):
    res = client.get(f"/api/v1/farms/{farm_with_rotation}/report.csv")
    body = res.content.decode("utf-8-sig").splitlines()
    start = body.index("# rotation")
    end = body.index("# scenarios")
    rows = [line for line in body[start + 1 : end] if line.strip()]
    assert len(rows) == 1 + 8, rows  # header + 8 seasons


def test_report_requires_a_rotation():
    res = client.post("/api/v1/farms", json={"demo_farm_id": "demo_greeley"})
    farm_id = res.json()["data"]["farm_id"]
    res = client.get(f"/api/v1/farms/{farm_id}/report.pdf")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"
