"""Bilingual output (D16): en-US default, es-ES supported.

The engine keeps English ids; translation lives in * _es.yaml catalogs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from rootshift import catalog
from rootshift.api.app import app

client = TestClient(app)


def test_crop_names_are_localised():
    assert catalog.crop_name("corn") == "Corn"
    assert catalog.crop_name("corn", "es-ES") == "Maíz"
    assert catalog.crop_name("winter_wheat", "es-ES") == "Trigo de invierno"


def test_every_crop_has_a_spanish_name():
    for crop_id in catalog.crop_ids():
        assert catalog.crop_name(crop_id, "es-ES") != crop_id


def test_every_disease_has_spanish_copy():
    for disease in catalog.diseases():
        es = catalog.disease_localised(disease["id"], "es-ES")
        assert es["locale"] == "es-ES", disease["id"]
        assert es["name"] and es["name"] != disease["name_en"]
        assert es["actions"]["cultural"], disease["id"]
        assert len(es["actions"]["cultural"]) == len(disease["actions"]["cultural"]), disease["id"]


def test_every_hazard_has_spanish_playbook():
    for hazard in catalog.hazards():
        es = catalog.hazard_localised(hazard["id"], "es-ES")
        assert es["locale"] == "es-ES", hazard["id"]
        assert es["name"] != hazard["name_en"]
        for stage in ("before", "during", "after"):
            assert len(es["playbook"][stage]) == len(hazard["playbook"][stage]), (hazard["id"], stage)


def test_localisation_falls_back_to_english():
    en = catalog.disease_localised("gray_leaf_spot_corn", "en-US")
    assert en["locale"] == "en-US"
    assert en["name"] == "Gray leaf spot"


@pytest.fixture(scope="module")
def farm_id():
    res = client.post("/api/v1/farms", json={"demo_farm_id": "demo_finney"})
    assert res.status_code == 201, res.text
    return res.json()["data"]["farm_id"]


def test_diseases_endpoint_serves_both_languages(farm_id):
    body = client.get(f"/api/v1/farms/{farm_id}/diseases").json()["data"]
    corn = next(c for c in body["crops"] if c["crop_id"] == "corn")
    disease = corn["diseases"][0]
    assert disease["name_en"] != disease["name_es"]
    assert disease["actions_es"]["cultural"]
    assert "caveat_codes" in body


def test_diseases_endpoint_honours_locale(farm_id):
    es = client.get(f"/api/v1/farms/{farm_id}/diseases?locale=es-ES").json()["data"]
    corn = next(c for c in es["crops"] if c["crop_id"] == "corn")
    assert corn["crop_name"] == "Maíz"
    assert es["caveats"][0].startswith("El mojado foliar")


def test_diseases_endpoint_honours_accept_language(farm_id):
    res = client.get(f"/api/v1/farms/{farm_id}/diseases", headers={"Accept-Language": "es-ES,es;q=0.9"})
    body = res.json()["data"]
    assert body["crops"][0]["crop_name"] == "Maíz"


def test_hazards_endpoint_serves_both_languages(farm_id):
    body = client.get(f"/api/v1/farms/{farm_id}/hazards").json()["data"]
    drought = next(h for h in body["hazards"] if h["hazard"] == "drought")
    assert drought["name"] == "Drought"
    assert drought["name_es"] == "Sequía"
    assert drought["playbook_es"]["before"][0] != drought["playbook"]["before"][0]


def test_hazards_endpoint_honours_locale(farm_id):
    body = client.get(f"/api/v1/farms/{farm_id}/hazards?locale=es-ES").json()["data"]
    drought = next(h for h in body["hazards"] if h["hazard"] == "drought")
    assert drought["name"] == "Sequía"
    assert drought["playbook"]["before"][0].startswith("Cambiar")


def test_playbook_endpoint_honours_locale(farm_id):
    body = client.get(f"/api/v1/farms/{farm_id}/hazards/drought/playbook?locale=es-ES").json()["data"]
    assert body["name"] == "Sequía"
    assert body["locale"] == "es-ES"
    assert body["playbook"]["before"][0].startswith("Cambiar")


def test_rotation_exposes_spanish_crop_names(farm_id):
    res = client.post(f"/api/v1/farms/{farm_id}/rotation:optimize", json={})
    job_id = res.json()["data"]["job_id"]
    for _ in range(200):
        payload = client.get(f"/api/v1/jobs/{job_id}").json()["data"]
        if payload["status"] in ("done", "failed"):
            break
    assert payload["status"] == "done"
    result = payload["result"]["result"]
    for item in result["sequence"]:
        assert item["crop_name_es"] and item["crop_name_es"] != item["crop_name"]
    assert result["irs"]["label_code"] in {
        "highly_resilient", "resilient", "vulnerable", "highly_vulnerable", "critical"
    }
