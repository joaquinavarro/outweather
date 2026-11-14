"""NASA GIBS imagery provider (real satellite imagery for F4).

GIBS (Global Imagery Browse Services) is a public NASA EOSDIS service with no
authentication. It serves WMS map images for MODIS/VIIRS layers on demand, which
is what lets the time map show the real field instead of a modelled series.

Note: this is a visualisation service, not an analysis product. The numeric
series still comes from the fixture/analytics path.
"""

from __future__ import annotations

import hashlib
import urllib.parse

from .. import config
from .base import USER_AGENT, _assert_online

GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"

LAYERS: dict[str, dict] = {
    "ndvi": {
        "wms_layer": "MODIS_Terra_L3_NDVI_16Day",
        "name": "NDVI (MODIS Terra, 16-day)",
        "short_name": "MOD13A2",
        "cadence_days": 16,
        "kind": "index",
        "attribution": "NASA GIBS / MODIS Terra",
        "start": "2000-02-18",
    },
    "ndvi_monthly": {
        "wms_layer": "MODIS_Terra_L3_NDVI_Monthly",
        "name": "NDVI (MODIS Terra, monthly)",
        "short_name": "MOD13A3",
        "cadence_days": 30,
        "kind": "index",
        "attribution": "NASA GIBS / MODIS Terra",
        "start": "2000-02-01",
    },
    "truecolor": {
        "wms_layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "name": "True color (MODIS Terra, daily)",
        "short_name": "MOD09",
        "cadence_days": 1,
        "kind": "rgb",
        "attribution": "NASA GIBS / MODIS Terra",
        "start": "2000-02-24",
    },
    "lst_day": {
        "wms_layer": "MODIS_Terra_L3_Land_Surface_Temp_8Day_Day",
        "name": "Land surface temperature, day (8-day)",
        "short_name": "MOD11A2",
        "cadence_days": 8,
        "kind": "temperature",
        "attribution": "NASA GIBS / MODIS Terra",
        "start": "2000-02-18",
    },
}


def layers_metadata() -> list[dict]:
    return [
        {
            "id": key,
            "name": meta["name"],
            "short_name": meta["short_name"],
            "cadence_days": meta["cadence_days"],
            "kind": meta["kind"],
            "attribution": meta["attribution"],
            "start": meta["start"],
        }
        for key, meta in LAYERS.items()
    ]


def _cache_file(layer: str, date: str, bbox: str, width: int, height: int):
    digest = hashlib.sha1(f"{layer}|{date}|{bbox}|{width}x{height}".encode()).hexdigest()[:16]
    folder = config.CACHE_DIR / "gibs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{layer}_{digest}.png"


def image_url(layer: str, date: str, bbox: str, width: int = 640, height: int = 420) -> str:
    meta = LAYERS[layer]
    min_lon, min_lat, max_lon, max_lat = [float(v) for v in bbox.split(",")]
    params = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": "1.3.0",
        "LAYERS": meta["wms_layer"],
        "CRS": "EPSG:4326",
        # WMS 1.3.0 + EPSG:4326 uses lat,lon axis order
        "BBOX": f"{min_lat},{min_lon},{max_lat},{max_lon}",
        "WIDTH": str(width),
        "HEIGHT": str(height),
        "FORMAT": "image/png",
        "TIME": date,
    }
    return GIBS_WMS + "?" + urllib.parse.urlencode(params)


def fetch_image(layer: str, date: str, bbox: str, width: int = 640, height: int = 420) -> bytes:
    if layer not in LAYERS:
        raise ValueError(f"unknown imagery layer: {layer}")
    _assert_online()

    cached = _cache_file(layer, date, bbox, width, height)
    if cached.exists():
        return cached.read_bytes()

    url = image_url(layer, date, bbox, width, height)
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()

    # A transparent 1x1 or a text error page is not an image we can use.
    if not data or len(data) < 200 or not data.startswith(b"\x89PNG"):
        raise RuntimeError("GIBS returned an unusable image")

    cached.write_bytes(data)
    return data
