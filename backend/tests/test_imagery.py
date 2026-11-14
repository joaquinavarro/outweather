"""NASA GIBS imagery provider and endpoints (F4 real satellite imagery)."""

from __future__ import annotations

import urllib.parse

import pytest
from fastapi.testclient import TestClient

from rootshift import config
from rootshift.api.app import app
from rootshift.providers import gibs

client = TestClient(app)

PNG_STUB = b"\x89PNG\r\n\x1a\n" + b"0" * 400


def test_image_url_uses_lat_lon_axis_order():
    url = gibs.image_url("ndvi", "2023-07-01", "-101.1,37.9,-100.7,38.2", 640, 420)
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert query["LAYERS"] == ["MODIS_Terra_L3_NDVI_16Day"]
    assert query["CRS"] == ["EPSG:4326"]
    # WMS 1.3.0 + EPSG:4326 is lat,lon
    assert query["BBOX"] == ["37.9,-101.1,38.2,-100.7"]
    assert query["TIME"] == ["2023-07-01"]
    assert query["WIDTH"] == ["640"]


def test_layers_metadata():
    layers = gibs.layers_metadata()
    ids = {layer["id"] for layer in layers}
    assert {"ndvi", "truecolor", "lst_day"} <= ids
    for layer in layers:
        assert layer["name"] and layer["attribution"].startswith("NASA GIBS")


def test_fetch_image_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        return FakeResponse(PNG_STUB)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    first = gibs.fetch_image("ndvi", "2023-07-01", "-101.1,37.9,-100.7,38.2", 320, 200)
    second = gibs.fetch_image("ndvi", "2023-07-01", "-101.1,37.9,-100.7,38.2", 320, 200)
    assert first == second == PNG_STUB
    assert len(calls) == 1, "second call should hit the disk cache"


def test_fetch_image_rejects_non_png(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)

    class FakeResponse:
        def read(self):
            return b"<html>error</html>"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: FakeResponse())
    with pytest.raises(RuntimeError):
        gibs.fetch_image("ndvi", "2023-07-01", "-101.1,37.9,-100.7,38.2", 320, 200)


def test_layers_endpoint():
    body = client.get("/api/v1/imagery/layers").json()
    assert len(body["data"]["layers"]) >= 3
    assert "GIBS" in body["data"]["attribution"]


def test_imagery_endpoint_returns_png(monkeypatch):
    monkeypatch.setattr(
        "rootshift.api.app.gibs.fetch_image",
        lambda layer, date, bbox, w, h: PNG_STUB,
    )
    res = client.get("/api/v1/imagery?layer=ndvi&date=2023-07-01&bbox=-101.1,37.9,-100.7,38.2")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content == PNG_STUB


def test_imagery_rejects_bad_bbox():
    res = client.get("/api/v1/imagery?layer=ndvi&date=2023-07-01&bbox=1,2,3")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_imagery_rejects_unknown_layer():
    res = client.get("/api/v1/imagery?layer=sar&date=2023-07-01&bbox=-101.1,37.9,-100.7,38.2")
    assert res.status_code == 400


def test_imagery_reports_upstream_failure(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("gibs down")

    monkeypatch.setattr("rootshift.api.app.gibs.fetch_image", boom)
    res = client.get("/api/v1/imagery?layer=ndvi&date=2023-07-01&bbox=-101.1,37.9,-100.7,38.2")
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "IMAGERY_UNAVAILABLE"

def test_layers_publish_the_archive_start():
    layers = {layer["id"]: layer for layer in gibs.layers_metadata()}
    for layer in layers.values():
        assert layer["start"] == layer["start"][:10]
    assert layers["ndvi"]["start"] == "2000-02-18"


def test_imagery_rejects_dates_before_the_archive(monkeypatch):
    called = []
    monkeypatch.setattr(
        "rootshift.api.app.gibs.fetch_image",
        lambda *a, **k: called.append(a) or PNG_STUB,
    )
    res = client.get("/api/v1/imagery?layer=ndvi&date=1991-01-01&bbox=-101.1,37.9,-100.7,38.2")
    assert res.status_code == 422
    body = res.json()["error"]
    assert body["code"] == "DATE_BEFORE_LAYER_START"
    assert body["layer_start"] == "2000-02-18"
    assert called == [], "must not call GIBS for a date outside the archive"


def test_imagery_accepts_the_first_day_of_the_archive(monkeypatch):
    monkeypatch.setattr("rootshift.api.app.gibs.fetch_image", lambda *a, **k: PNG_STUB)
    res = client.get("/api/v1/imagery?layer=ndvi&date=2000-02-18&bbox=-101.1,37.9,-100.7,38.2")
    assert res.status_code == 200
