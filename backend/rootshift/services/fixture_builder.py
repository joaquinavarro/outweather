"""Build a field fixture from live providers (POWER + SSURGO).

This is the custom-field path: the user gives coordinates and an area, and we
fetch the real climate and soil for that spot, synthesising the rest exactly as
the demo fixtures do. The result is cached on disk so the second visit is free.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from .. import catalog, config
from ..domain.climate import eto_fao56
from ..domain.water import taw_mm
from ..providers import base as provider_base
from ..providers import power as power_provider
from ..providers import ssurgo as soil_provider

GEOD_EARTH_RADIUS_M = 6378137.0
METERS_PER_DEG_LAT = 111_320.0

GAEZ_MULTIPLIERS = {
    "corn": {"rcp45": (0.95, 1.15), "rcp85": (0.88, 1.30)},
    "soybean": {"rcp45": (0.96, 1.12), "rcp85": (0.90, 1.25)},
    "winter_wheat": {"rcp45": (0.97, 1.10), "rcp85": (0.92, 1.22)},
    "grain_sorghum": {"rcp45": (0.98, 1.08), "rcp85": (0.94, 1.18)},
    "alfalfa": {"rcp45": (0.97, 1.12), "rcp85": (0.93, 1.24)},
    "oats": {"rcp45": (0.96, 1.10), "rcp85": (0.90, 1.20)},
    "sunflower": {"rcp45": (0.95, 1.14), "rcp85": (0.89, 1.28)},
    "canola": {"rcp45": (0.95, 1.12), "rcp85": (0.89, 1.26)},
    "cereal_rye": {"rcp45": (0.97, 1.06), "rcp85": (0.93, 1.15)},
}

PILOT_STATE_CODES = {"KS", "NE", "OK", "CO"}


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def polygon_from_center(lat: float, lon: float, area_ha: float) -> tuple[list[list[float]], float]:
    """Square parcel of the requested area, centred on (lat, lon)."""
    side_m = math.sqrt(max(area_ha, 0.01) * 10_000.0)
    dlat = (side_m / 2.0) / METERS_PER_DEG_LAT
    dlon = (side_m / 2.0) / (METERS_PER_DEG_LAT * max(math.cos(math.radians(lat)), 0.05))
    ring = [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
        [lon - dlon, lat - dlat],
    ]
    return ring, area_ha


def polygon_area_ha(ring: list[list[float]]) -> float:
    """Spherical excess area of a closed lon/lat ring, in hectares."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring[:-1], ring[1:]):
        total += math.radians(x2 - x1) * (
            2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2))
        )
    return abs(total * GEOD_EARTH_RADIUS_M * GEOD_EARTH_RADIUS_M / 2.0) / 10_000.0


def polygon_centroid(ring: list[list[float]]) -> tuple[float, float]:
    """Area-weighted centroid of a lon/lat ring -> (lat, lon)."""
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)
    if len(pts) < 3:
        raise ValueError("POLYGON_TOO_SMALL: at least 3 vertices are needed")
    area2 = 0.0
    cx = 0.0
    cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        cross = x1 * y2 - x2 * y1
        area2 += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(area2) < 1e-12:
        # degenerate (all points on a line): fall back to the vertex mean
        return sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)
    return cy / (3 * area2), cx / (3 * area2)


def normalise_ring(ring: list[list[float]]) -> list[list[float]]:
    """Validate a drawn field polygon and return it closed, [lon, lat]."""
    if not isinstance(ring, list) or len(ring) < 3:
        raise ValueError("POLYGON_TOO_SMALL: draw at least 3 vertices")
    clean: list[list[float]] = []
    for point in ring:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            raise ValueError("POLYGON_INVALID: vertices must be [lon, lat] pairs")
        lon, lat = float(point[0]), float(point[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("POLYGON_INVALID: longitude/latitude out of range")
        clean.append([round(lon, 6), round(lat, 6)])
    if clean[0] != clean[-1]:
        clean.append(clean[0])
    if len(clean) < 4:  # 3 distinct vertices + closing point
        raise ValueError("POLYGON_TOO_SMALL: draw at least 3 vertices")
    if len({(p[0], p[1]) for p in clean[:-1]}) < 3:
        raise ValueError("POLYGON_TOO_SMALL: the vertices must not be collinear")

    centroid_lat = sum(p[1] for p in clean[:-1]) / (len(clean) - 1)
    centroid_lon = sum(p[0] for p in clean[:-1]) / (len(clean) - 1)
    if not (24.0 <= centroid_lat <= 50.0 and -125.0 <= centroid_lon <= -66.0):
        raise ValueError("LOCATION_OUT_OF_US")

    area = polygon_area_ha(clean)
    if area < 0.5:
        raise ValueError(f"POLYGON_TOO_SMALL: {area:.2f} ha is below the 0.5 ha minimum")
    if area > 5000:
        raise ValueError(f"POLYGON_TOO_LARGE: {area:.0f} ha exceeds the 5000 ha limit")
    return clean


# --------------------------------------------------------------------------
# county resolution
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _county_index() -> dict[tuple[str, str], dict]:
    payload = yaml.safe_load((Path(config.CATALOG_DIR) / "counties_us.yaml").read_text(encoding="utf-8"))
    index = {}
    for row in payload["counties"]:
        key = (row["county"].strip().lower(), row["state"].strip().lower())
        index[key] = row
    return index


def _normalise_county(name: str) -> str:
    return name.lower().replace(" county", "").strip()


def resolve_county(lat: float, lon: float) -> dict:
    """Reverse geocode the point and map it to a SSURGO areasymbol."""
    if not (24.0 <= lat <= 50.0 and -125.0 <= lon <= -66.0):
        raise ValueError("LOCATION_OUT_OF_US")

    key = f"{lat:.3f}:{lon:.3f}"
    cached = provider_base.read_cache("county", key)
    if cached:
        return cached

    url = (
        "https://nominatim.openstreetmap.org/reverse?format=json&zoom=10&addressdetails=1"
        f"&lat={lat:.5f}&lon={lon:.5f}"
    )
    try:
        payload = provider_base.http_json(url, timeout=30, retries=2)
    except Exception as exc:  # network down or rate limited
        raise ValueError(f"COUNTY_LOOKUP_FAILED: {exc}") from exc

    address = payload.get("address", {})
    county_name = address.get("county") or address.get("city") or ""
    state_name = address.get("state") or ""
    state_code = address.get("state_code", "")

    entry = _county_index().get((_normalise_county(county_name), state_name.lower()))
    if entry is None:
        # fall back to matching by state code prefix + county name
        for (county, _state), row in _county_index().items():
            if county == _normalise_county(county_name) and row["state_code"] == state_code:
                entry = row
                break

    if entry is None:
        raise ValueError(f"COUNTY_NOT_IN_PILOT: {county_name}, {state_name}")
    if entry["state_code"] not in PILOT_STATE_CODES:
        raise ValueError(f"STATE_NOT_IN_PILOT: {state_code}")

    provider_base.write_cache("county", key, entry)
    return entry


# --------------------------------------------------------------------------
# synthetic layers (shared with the demo fixture builder)
# --------------------------------------------------------------------------

def synthesize(seed_key: str, weather: dict, soil: dict) -> dict:
    seed = int(hashlib.sha1(seed_key.encode()).hexdigest()[:8], 16) % (2**31)
    rng = np.random.default_rng(seed)

    tmax = np.array(weather["tmax"], float)
    tmin = np.array(weather["tmin"], float)
    pr = np.nan_to_num(np.array(weather["pr"], float), nan=0.0)
    et0 = np.array(weather["et0"], float)
    dates = weather["dates"]
    n = len(dates)
    doy = np.array([dt.date(int(d[:4]), int(d[4:6]), int(d[6:])).timetuple().tm_yday for d in dates])

    zr = 1.5
    taw = taw_mm(soil["theta_fc"], soil["theta_wp"], zr)
    d = 0.5 * taw
    sm_frac = np.zeros(n)
    for i in range(n):
        d = d - pr[i] + 0.8 * et0[i]
        d = min(max(d, 0.0), taw)
        sm_frac[i] = (taw - d) / taw
    theta = soil["theta_wp"] + sm_frac * (soil["theta_fc"] - soil["theta_wp"])
    theta = np.clip(theta + rng.normal(0, 0.008, n), 0.02, 0.55)

    seasonal = np.maximum(0.0, np.sin(np.pi * (doy - 100) / 170.0))
    ndvi = 0.18 + 0.60 * seasonal * (0.75 + 0.25 * sm_frac) + rng.normal(0, 0.02, n)
    ndvi = np.clip(ndvi, 0.05, 0.92)

    lst_night = tmin + 1.5 + rng.normal(0, 0.8, n)

    years = sorted({int(d[:4]) for d in dates})
    year_arr = np.array([int(d[:4]) for d in dates])
    annual_pr = {y: float(np.nansum(pr[year_arr == y])) for y in years}
    npp, nee, runoff = {}, {}, {}
    for y in years:
        mask = year_arr == y
        npp[y] = round(float(320 + 420 * np.mean(ndvi[mask]) + rng.normal(0, 15)), 1)
        nee[y] = round(float(-0.35 * npp[y] + rng.normal(0, 25)), 1)
        runoff[y] = round(0.05 * annual_pr[y], 1)

    return {
        "synthetic": True,
        "sm_rz": [round(float(v), 4) for v in theta],
        "lst_night_c": [round(float(v), 2) for v in lst_night],
        "ndvi_daily": [round(float(v), 4) for v in ndvi],
        "npp_gc_m2_year": npp,
        "nee_gc_m2_year": nee,
        "runoff_mm_year": runoff,
        "cocorahs": {"r": 0.78, "bias": -0.04, "stations": 3},
    }


def gaez_block() -> dict:
    return {
        crop: {
            "rcp45": {"yield_multiplier": v["rcp45"][0], "water_multiplier": v["rcp45"][1]},
            "rcp85": {"yield_multiplier": v["rcp85"][0], "water_multiplier": v["rcp85"][1]},
        }
        for crop, v in GAEZ_MULTIPLIERS.items()
    }


# --------------------------------------------------------------------------
# custom fixture
# --------------------------------------------------------------------------

def build_custom_fixture(
    lat: float,
    lon: float,
    area_ha: float,
    name: str,
    irrigation_status: str = "rainfed",
    irrigation_system: str = "none",
    current_crop_id: str | None = None,
    use_cache: bool = True,
    ring: list[list[float]] | None = None,
) -> dict:
    """Build a fixture for a custom field.

    `ring` is the polygon drawn on the map ([lon, lat], closed). When given, it
    replaces the generated square and its geodesic area is used.
    `current_crop_id` of ``None``/``""`` means the farmer has nothing planted
    ("None" in the design panel): the fixture then has an empty current-crop list.
    """
    crop_id = current_crop_id if (current_crop_id and current_crop_id in catalog.crops()) else None
    if ring is not None:
        ring = normalise_ring(ring)
        area = polygon_area_ha(ring)
        key = f"{lat:.5f}:{lon:.5f}:{crop_id or 'none'}:{hashlib.sha1(json.dumps(ring).encode()).hexdigest()[:10]}"
    else:
        ring, area = polygon_from_center(lat, lon, area_ha)
        key = f"{lat:.4f}:{lon:.4f}:{area_ha:.1f}:{crop_id or 'none'}"
    digest = hashlib.sha1(key.encode()).hexdigest()[:12]
    cache_path = Path(config.CACHE_DIR) / f"custom_{digest}.json"
    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    county = resolve_county(lat, lon)

    pwr = power_provider.fetch_daily(lat, lon, "19910101", "20241231")
    arrays = power_provider.daily_arrays(pwr)
    elevation = float(arrays["cell"].get("elevation_m") or 300.0)
    et0 = eto_fao56(
        arrays["tmax"], arrays["tmin"], arrays["tdew"], arrays["rs"], arrays["ws"], arrays["ps"],
        lat, arrays["doy"], elevation,
    )
    weather = {
        "dates": [d.replace("-", "") for d in arrays["date"]],
        "tmax": [round(float(v), 2) for v in arrays["tmax"]],
        "tmin": [round(float(v), 2) for v in arrays["tmin"]],
        "tdew": [round(float(v), 2) for v in arrays["tdew"]],
        "rh": [round(float(v), 2) for v in arrays["rh"]],
        "ws": [round(float(v), 2) for v in arrays["ws"]],
        "rs": [round(float(v), 2) for v in arrays["rs"]],
        "ps": [round(float(v), 2) for v in arrays["ps"]],
        "pr": [round(float(v), 2) for v in arrays["pr"]],
        "et0": [round(float(v), 2) for v in et0],
        "cell": arrays["cell"],
    }

    try:
        soil = soil_provider.fetch_soil(ring, county["areasymbol"])
    except Exception:
        soil = soil_provider.default_soil()

    synthetic = synthesize(key, weather, soil)

    fixture = {
        "farm": {
            "id": f"custom_{digest}",
            "name": name or f"Custom field ({lat:.3f}, {lon:.3f})",
            "region_id": "us_ks",
            "county": county["county"],
            "label": f"Custom field · {irrigation_status}",
            "location": {"lat": round(lat, 5), "lon": round(lon, 5)},
            "boundary": ring,
            "area_ha": round(area, 1),
            "production_system": "conventional",
            "irrigation": {
                "status": irrigation_status,
                "system": irrigation_system if irrigation_status == "irrigated" else "none",
                "flow_l_s": 40 if irrigation_status == "irrigated" else 0,
                "annual_limit_m3": (180000 if irrigation_status == "irrigated" else 0),
                "energy": "grid" if irrigation_status == "irrigated" else "none",
                "hours_per_day": 20 if irrigation_status == "irrigated" else 0,
            },
            "current_crops": [
                {
                    "crop_id": crop_id,
                    "area_ha": round(area, 1),
                    "season": "2025",
                }
            ] if crop_id else [],
            "resources": {
                "machinery": ["tractor_180hp", "planter", "combine", "sprayer"],
                "labor": {"permanent": 1, "seasonal": 2},
                "fertility": {"n_kg_ha": 150, "p2o5_kg_ha": 50, "k2o_kg_ha": 30},
                "cover_crop_seed": True,
                "storage_t": 300,
            },
        },
        "weather": weather,
        "soil": soil,
        "synthetic": synthetic,
        "gaez": gaez_block(),
        "meta": {
            "built_at": dt.datetime.now().isoformat(timespec="seconds"),
            "real_products": ["NASA POWER daily (P15)", "SSURGO (P16)"],
            "synthetic_products": ["SMAP L4", "SMAP L4 Carbon", "MOD13Q1", "MOD11A2", "MOD17A3HGF",
                                   "GLDAS runoff", "GAEZ v4 multipliers", "CoCoRaHS validation"],
            "county": county,
        },
    }

    config.ensure_dirs()
    cache_path.write_text(json.dumps(fixture), encoding="utf-8")
    fixture["meta"]["cache_path"] = str(cache_path)
    return fixture
