"""Scenario definitions and perturbation rules (spec 10.6).

S0-S5 are historical resampling and perturbations; S6/S7 apply FAO GAEZ v4
crop-level climate multipliers for the 2050s. GAEZ uses RCP (AR5), never SSP.
"""

from __future__ import annotations

import numpy as np

SCENARIO_DEFS: list[dict] = [
    {"id": "S0", "name": "Historical", "pool": "all", "label": "Historical resampling 2001-2024"},
    {"id": "S1", "name": "Severe drought", "pool": "drought", "label": "Years with SPEI-12 <= -1.5"},
    {"id": "S2", "name": "Multi-year drought", "pool": "drought3", "label": "Three consecutive dry years"},
    {"id": "S3", "name": "Heat at flowering", "pool": "all", "heat_delta": 3.0, "label": "+3 C during flowering"},
    {"id": "S4", "name": "Extreme rainfall", "pool": "all", "rain_mult": 1.5, "label": "Rx1day x1.5"},
    {"id": "S5", "name": "Late frost", "pool": "all", "frost_shift": 14, "label": "Last frost +14 days"},
    {"id": "S6", "name": "2050s RCP4.5", "pool": "all", "gaez": "rcp45", "label": "GAEZ 2050s RCP4.5"},
    {"id": "S7", "name": "2050s RCP8.5", "pool": "all", "gaez": "rcp85", "label": "GAEZ 2050s RCP8.5"},
]

SCENARIO_BY_ID = {s["id"]: s for s in SCENARIO_DEFS}


def scenario_meta(scenario_id: str) -> dict:
    return SCENARIO_BY_ID[scenario_id]


def build_pools(years: list[int], spei12_by_year: dict[int, float]) -> dict[str, list[int]]:
    """Year pools used by each scenario family."""
    all_years = sorted(set(int(y) for y in years))
    ranked = sorted(all_years, key=lambda y: spei12_by_year.get(y, 0.0))
    drought = [y for y in all_years if spei12_by_year.get(y, 0.0) <= -1.5]
    if len(drought) < 3:
        drought = ranked[: max(3, len(all_years) // 5)]
    start_pool = ranked[: max(3, len(all_years) // 5)]
    return {"all": all_years, "drought": sorted(drought), "drought3": sorted(start_pool)}


def build_members(pools: dict[str, list[int]], scenario_id: str, n_seasons: int, n_members: int, seed: int) -> np.ndarray:
    """Return an (n_members, n_seasons) matrix of year indices."""
    cfg = scenario_meta(scenario_id)
    rng = np.random.default_rng(seed + sum(ord(c) for c in scenario_id))
    pool = pools[cfg["pool"]]
    if not pool:
        pool = pools["all"]

    if cfg["pool"] == "drought3":
        starts = np.array(pool, dtype=int)
        out = np.empty((n_members, n_seasons), dtype=int)
        for i in range(n_members):
            start = int(rng.choice(starts))
            for k in range(n_seasons):
                out[i, k] = start + (k % 3)
        return out

    arr = np.array(pool, dtype=int)
    return rng.choice(arr, size=(n_members, n_seasons), replace=True)


def scenario_adjustment(crop: dict, scenario_id: str, gaez: dict | None = None) -> tuple[float, float]:
    """(yield multiplier, irrigation-demand multiplier) for a scenario.

    S3/S4/S5 are perturbation approximations on top of the historical matrix;
    they are documented as such in the UI caveats.
    """
    cfg = scenario_meta(scenario_id)
    y_mult, w_mult = 1.0, 1.0

    if scenario_id == "S3":
        y_mult *= 0.93
    elif scenario_id == "S4":
        y_mult *= 0.97
        w_mult *= 0.70
    elif scenario_id == "S5":
        y_mult *= 0.96
    elif scenario_id in ("S6", "S7") and gaez:
        key = cfg.get("gaez")
        entry = (gaez or {}).get(crop["id"], {}).get(key, {})
        y_mult *= float(entry.get("yield_multiplier", 1.0))
        w_mult *= float(entry.get("water_multiplier", 1.0))

    return y_mult, w_mult
