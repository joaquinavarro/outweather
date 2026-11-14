"""Build offline fixtures for the three Kansas demo farms.

Real data: NASA POWER daily (1991-2024) and USDA SSURGO soil.
Everything else in the fixture is SYNTHETIC and labeled as such: SMAP soil
moisture, MODIS NDVI/LST/NPP, SMAP carbon, GLDAS runoff and GAEZ multipliers.
The demo works with the network unplugged (D18) and the UI says "demo data".
"""

from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
from pyproj import Geod

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rootshift import catalog, config  # noqa: E402
from rootshift.domain.water import taw_mm  # noqa: E402
from rootshift.providers import power as power_provider  # noqa: E402
from rootshift.providers import ssurgo as soil_provider  # noqa: E402

GEOD = Geod(ellps="WGS84")

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


def polygon_for(center: dict, radius: dict) -> tuple[list[list[float]], float]:
    lat, lon = center["lat"], center["lon"]
    dlat, dlon = radius["lat"], radius["lon"]
    ring = [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
        [lon - dlon, lat - dlat],
    ]
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    area_m2, _ = GEOD.polygon_area_perimeter(lons, lats)
    return ring, abs(area_m2) / 10000.0


def synthesize(farm: dict, weather: dict, soil: dict, area_ha: float) -> dict:
    seed = int(farm["id"].replace("demo_", "").__len__()) + sum(ord(c) for c in farm["id"])
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
    annual_pr = {y: float(np.nansum(pr[np.array([int(x[:4]) for x in dates]) == y])) for y in years}
    npp = {}
    nee = {}
    runoff = {}
    for y in years:
        mask = np.array([int(x[:4]) == y for x in dates])
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


def build_one(farm) -> dict:
    ring, area_ha = polygon_for(farm.location, farm.parcel_radius_deg)
    region = catalog.region(farm.region_id)
    county = next(c for c in region.counties if c["name"] == farm.county)

    print(f"[{farm.id}] POWER 1991-2024 ...")
    pwr = power_provider.fetch_daily(farm.location["lat"], farm.location["lon"], "19910101", "20241231")
    arrays = power_provider.daily_arrays(pwr)

    from rootshift.domain.climate import eto_fao56

    elev = float(arrays["cell"].get("elevation_m") or 300.0)
    et0 = eto_fao56(
        arrays["tmax"], arrays["tmin"], arrays["tdew"], arrays["rs"], arrays["ws"], arrays["ps"],
        farm.location["lat"], arrays["doy"], elev,
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

    print(f"[{farm.id}] SSURGO {county['areasymbol']} ...")
    try:
        soil = soil_provider.fetch_soil(ring, county["areasymbol"])
    except Exception as exc:
        print(f"  soil fallback: {exc}")
        soil = soil_provider.default_soil()

    synthetic = synthesize(
        {"id": farm.id},
        {"dates": [d.replace("-", "") for d in arrays["date"]],
         "tmax": arrays["tmax"], "tmin": arrays["tmin"], "pr": arrays["pr"], "et0": et0},
        soil,
        area_ha,
    )
    synthetic["sm_rz"] = synthetic["sm_rz"]
    synthetic["ndvi_daily"] = synthetic["ndvi_daily"]

    current = [
        {
            "crop_id": c["crop_id"],
            "area_ha": round(area_ha * c["area_share"], 2),
            "season": "2025",
        }
        for c in farm.current_crops
    ]

    return {
        "farm": {
            "id": farm.id,
            "name": farm.name,
            "region_id": farm.region_id,
            "county": farm.county,
            "label": farm.label,
            "location": farm.location,
            "boundary": ring,
            "area_ha": round(area_ha, 1),
            "production_system": farm.production_system,
            "irrigation": farm.irrigation,
            "current_crops": current,
            "resources": farm.resources,
        },
        "weather": weather,
        "soil": soil,
        "synthetic": synthetic,
        "gaez": {
            crop: {
                "rcp45": {"yield_multiplier": v["rcp45"][0], "water_multiplier": v["rcp45"][1]},
                "rcp85": {"yield_multiplier": v["rcp85"][0], "water_multiplier": v["rcp85"][1]},
            }
            for crop, v in GAEZ_MULTIPLIERS.items()
        },
        "meta": {
            "built_at": dt.datetime.now().isoformat(timespec="seconds"),
            "real_products": ["NASA POWER daily (P15)", "SSURGO (P16)"],
            "synthetic_products": [
                "SMAP L4 soil moisture (P01)",
                "SMAP L4 Carbon (P03)",
                "MOD13Q1 NDVI (P06)",
                "MOD11A2 night LST (P07)",
                "MOD17A3HGF NPP (P09)",
                "GLDAS runoff (P13)",
                "GAEZ v4 multipliers (P18)",
                "CoCoRaHS validation (P22)",
            ],
        },
    }


def main() -> None:
    config.ensure_dirs()
    built = []
    for reg in catalog.regions().values():
        for farm in reg.demo_farms:
            payload = build_one(farm)
            path = config.FIXTURES_DIR / f"{farm.id}.json"
            with path.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            built.append((farm.id, path.stat().st_size / 1024))
            print(f"  -> {path.name} ({path.stat().st_size/1024:.0f} KB)")
    print("done:", built)


if __name__ == "__main__":
    main()
