"""Typed access to the YAML catalogs.

The catalogs are the product's data layer: crops, diseases, nutrients, hazards,
rotation effects, scoring weights, dataset registry and regions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import yaml

from .config import CATALOG_DIR, CONFIG_DIR


def _load(path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass(frozen=True)
class Crop:
    id: str
    name_en: str
    name_sci: str
    family: str
    cycle_type: str
    stand_seasons: int
    is_legume: bool
    season: str
    cover: bool
    kc: dict[str, float]
    stage_days: dict[str, int]
    zr_max_m: float
    p_depletion: float
    gdd_base_c: float
    gdd_to_maturity: float
    ky: float
    t_frost_critical_c: float
    t_heat_critical_c: float
    flowering_window_days: int
    hse_ref: float
    fse_ref: float
    sowing_window: list[dict[str, int]]
    source: str

    @property
    def kc_mid(self) -> float:
        return float(self.kc["mid"])

    @property
    def is_perennial(self) -> bool:
        return self.cycle_type == "perennial"

    @property
    def season_length_days(self) -> int:
        return int(sum(self.stage_days.values()))

    def sow_doy(self) -> int:
        window = self.sowing_window[0] if self.sowing_window else {"doy_from": 110}
        return int(window["doy_from"])

    def harvest_doy(self) -> int:
        return self.sow_doy() + self.season_length_days


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    country: str
    state_fips: str
    seasons_per_year: int
    utm_epsg: int
    crops: list[str]
    counties: list[dict[str, Any]]
    demo_farms: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class DemoFarm:
    id: str
    name: str
    county: str
    label: str
    location: dict[str, float]
    parcel_radius_deg: dict[str, float]
    production_system: str
    irrigation: dict[str, Any]
    current_crops: list[dict[str, Any]]
    resources: dict[str, Any]
    region_id: str = "us_ks"


# --------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _crops_raw() -> dict:
    return _load(CATALOG_DIR / "crops.yaml")


@lru_cache(maxsize=1)
def crops() -> dict[str, Crop]:
    out: dict[str, Crop] = {}
    for item in _crops_raw()["crops"]:
        out[item["id"]] = Crop(**item)
    return out


def crop(crop_id: str) -> Crop:
    return crops()[crop_id]


def crop_ids() -> list[str]:
    return list(crops().keys())


@lru_cache(maxsize=1)
def diseases() -> list[dict]:
    return _load(CATALOG_DIR / "diseases.yaml")["diseases"]


@lru_cache(maxsize=1)
def _diseases_es() -> dict[str, dict]:
    path = CATALOG_DIR / "diseases_es.yaml"
    if not path.exists():
        return {}
    return _load(path)["diseases"]


@lru_cache(maxsize=1)
def _hazards_es() -> dict[str, dict]:
    path = CATALOG_DIR / "hazards_es.yaml"
    if not path.exists():
        return {}
    return _load(path)["hazards"]


@lru_cache(maxsize=1)
def _crops_es() -> dict[str, str]:
    path = CATALOG_DIR / "crops_es.yaml"
    if not path.exists():
        return {}
    return _load(path)["crops"]


def crop_name(crop_id: str, locale: str = "en-US") -> str:
    if locale.startswith("es"):
        return _crops_es().get(crop_id, crops()[crop_id].name_en)
    return crops()[crop_id].name_en


def disease_localised(disease_id: str, locale: str = "en-US") -> dict:
    """Return {name, actions} in the requested locale, falling back to English."""
    base = next(d for d in diseases() if d["id"] == disease_id)
    if not locale.startswith("es"):
        return {"name": base["name_en"], "actions": base["actions"], "locale": "en-US"}
    es = _diseases_es().get(disease_id)
    if not es:
        return {"name": base["name_en"], "actions": base["actions"], "locale": "en-US"}
    return {"name": es["name"], "actions": es["actions"], "locale": "es-ES"}


def hazard_localised(hazard_id: str, locale: str = "en-US") -> dict:
    base = hazard(hazard_id)
    if not locale.startswith("es"):
        return {"name": base["name_en"], "playbook": base["playbook"], "locale": "en-US"}
    es = _hazards_es().get(hazard_id)
    if not es:
        return {"name": base["name_en"], "playbook": base["playbook"], "locale": "en-US"}
    return {"name": es["name"], "playbook": es["playbook"], "locale": "es-ES"}


def diseases_for(crop_id: str) -> list[dict]:
    return [d for d in diseases() if crop_id in d["crops"]]


@lru_cache(maxsize=1)
def hazards() -> list[dict]:
    return _load(CATALOG_DIR / "hazards.yaml")["hazards"]


def hazard(hazard_id: str) -> dict:
    for h in hazards():
        if h["id"] == hazard_id:
            return h
    raise KeyError(hazard_id)


@lru_cache(maxsize=1)
def nutrients() -> dict[str, dict]:
    raw = _load(CATALOG_DIR / "nutrients.yaml")["coefficients"]
    return {row["crop_id"]: row for row in raw}


@lru_cache(maxsize=1)
def scoring() -> dict:
    return _load(CATALOG_DIR / "scoring.yaml")


@lru_cache(maxsize=1)
def rotation_effects() -> dict:
    return _load(CATALOG_DIR / "rotation_effects.yaml")


@lru_cache(maxsize=1)
def sources() -> dict:
    return _load(CATALOG_DIR / "sources.yaml")


def product(product_id: str) -> dict:
    for p in sources()["products"]:
        if p["id"] == product_id:
            return p
    raise KeyError(product_id)


@lru_cache(maxsize=1)
def _regions_raw() -> dict:
    return _load(CONFIG_DIR / "regions" / "us_ks.yaml")


@lru_cache(maxsize=1)
def regions() -> dict[str, Region]:
    out: dict[str, Region] = {}
    for item in _regions_raw()["regions"]:
        demo = [DemoFarm(**{**f, "region_id": item["id"]}) for f in item.get("demo_farms", [])]
        payload = {k: v for k, v in item.items() if k != "demo_farms"}
        out[item["id"]] = Region(**payload, demo_farms=demo)
    return out


def region(region_id: str = "us_ks") -> Region:
    return regions()[region_id]


def demo_farm(farm_id: str) -> DemoFarm:
    for reg in regions().values():
        for farm in reg.demo_farms:
            if farm.id == farm_id:
                return farm
    raise KeyError(farm_id)
