"""Yield model (spec 10.5): FAO-33 water-limited plus thermal factors.

Y_sim = Ym * [1 - Ky * (1 - ETa/ETm)] * f_heat * f_frost * f_rot
"""

from __future__ import annotations

import math


def rho_et(eta_mm: float, etm_mm: float) -> float:
    """Actual-to-maximum ET ratio, clamped to [0, 1]."""
    if etm_mm <= 0:
        return 1.0
    return max(0.0, min(1.0, float(eta_mm) / float(etm_mm)))


def water_limited_ratio(ky: float, rho: float) -> float:
    """FAO-33: relative yield (0-1) from the ET deficit."""
    return max(0.0, min(1.0, 1.0 - ky * (1.0 - rho)))


def heat_factor(hse: float, ref: float, k: float = 0.25, floor: float = 0.75) -> float:
    """Heat penalty. Capped at 25% so a hot flowering window does not halve the yield."""
    if ref <= 0:
        return 1.0
    return max(floor, 1.0 - k * min(1.0, max(0.0, hse) / ref))


def frost_factor(fse: float, ref: float, k: float = 0.5, floor: float = 0.5) -> float:
    if ref <= 0:
        return 1.0
    return max(floor, 1.0 - k * min(1.0, max(0.0, fse) / ref))


def rotation_multiplier(effects_cfg: dict, prev: dict | None, cur: dict) -> float:
    """Effect of the previous crop on the current one (spec 10.7.5)."""
    if prev is None:
        return float(effects_cfg.get("default", 1.0))

    for pair in effects_cfg.get("pairs", []):
        if pair["from"] != prev["id"]:
            continue
        if pair["to"] == "*" or pair["to"] == cur["id"]:
            return float(pair["value"])

    for rule in effects_cfg.get("rules", []):
        if rule.get("from_same_as_to") and prev["id"] == cur["id"]:
            return float(rule["value"])
        fam_from = rule.get("from_family")
        fam_to = rule.get("to_family")
        if rule.get("from_family_equals_to_family") and prev["family"] == cur["family"]:
            return float(rule["value"])
        if fam_from and fam_to and prev["family"] == fam_from and cur["family"] == fam_to:
            return float(rule["value"])

    return float(effects_cfg.get("default", 1.0))


def simulated_yield(
    ym_t_ha: float,
    ky: float,
    rho: float,
    hse: float,
    fse: float,
    hse_ref: float,
    fse_ref: float,
    f_rot: float,
    k_heat: float = 0.25,
    k_frost: float = 0.5,
) -> dict:
    y_water = water_limited_ratio(ky, rho)
    fh = heat_factor(hse, hse_ref, k_heat)
    ff = frost_factor(fse, fse_ref, k_frost)
    rel = max(0.0, min(1.0, y_water * fh * ff * f_rot))
    return {
        "yield_rel": rel,
        "yield_t_ha": max(0.0, ym_t_ha * rel),
        "water_rel": y_water,
        "heat_factor": fh,
        "frost_factor": ff,
        "rotation_factor": f_rot,
    }


def gdd_window_ok(gdd_available: float, gdd_needed: float, tolerance: float = 0.9) -> bool:
    return gdd_available >= tolerance * gdd_needed


def log_safe(x: float) -> float:
    return math.log(max(x, 1e-9))
