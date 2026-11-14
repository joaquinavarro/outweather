"""Global configuration and paths.

All tunable numbers live in data/catalog/*.yaml or config/*.yaml, not here.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
CATALOG_DIR = DATA_DIR / "catalog"
FIXTURES_DIR = DATA_DIR / "fixtures"
CACHE_DIR = DATA_DIR / "cache"
CONFIG_DIR = BACKEND_DIR / "config"

MODEL_VERSION = "2.0.0"

# Simulation window: IMERG + MODIS coverage (spec 10.1).
SIM_START = 2001
SIM_END = 2024

# Climatological normals for temperature-type indices (spec 10.1).
NORMALS_START = 1991
NORMALS_END = 2020

# SMAP baseline for soil-moisture percentiles.
SMAP_BASELINE_START = 2015
SMAP_BASELINE_END = 2024

SEED = 42


def data_mode() -> str:
    """demo | cached | live. Default is demo so the app works offline."""
    return os.getenv("DATA_MODE", "demo").strip().lower()


def is_demo() -> bool:
    return data_mode() == "demo"


def db_path() -> Path:
    """SQLite file for the MVP store. Override with ROOTSHIFT_DB (tests do)."""
    raw = os.getenv("ROOTSHIFT_DB")
    if raw:
        return Path(raw)
    return CACHE_DIR / "rootshift.sqlite3"


def ensure_dirs() -> None:
    for path in (FIXTURES_DIR, CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)
