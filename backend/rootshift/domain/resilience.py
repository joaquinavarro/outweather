"""ROOTSHIFT Resilience Index (spec 10.9).

A composite, product-specific index. It is NOT a scientific standard and the UI
must say so. Every sub-index is 0-100 and its weighted contribution is exported
for the breakdown chart.
"""

from __future__ import annotations

import math


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def water_index(rho_et: float, coverage: float, groundwater_status: str, groundwater_trend: float, cfg: dict) -> tuple[float, dict]:
    gw_cfg = cfg["irs"]["water"]
    if groundwater_status in ("stable", "rising", None):
        gw = 1.0
    elif groundwater_trend is not None and groundwater_trend < gw_cfg["groundwater_critical_mm_year"]:
        gw = gw_cfg["groundwater_penalty_critical"]
    else:
        gw = gw_cfg["groundwater_penalty_declining"]
    value = 100.0 * (
        gw_cfg["et_ratio_weight"] * _clamp(rho_et)
        + gw_cfg["coverage_weight"] * _clamp(coverage)
        + gw_cfg["groundwater_weight"] * gw
    )
    return value, {"et_ratio": _clamp(rho_et), "coverage": _clamp(coverage), "groundwater": gw}


def stability_index(cv: float, p_fail: float, cfg: dict) -> float:
    ceiling = cfg["irs"]["stability"]["cv_ceiling"]
    return 100.0 * (1.0 - _clamp(cv / ceiling)) * (1.0 - _clamp(p_fail))


def soil_index(
    nee: float | None,
    npp: float | None,
    erosion: float,
    legume_fraction: float,
    nitrogen_balance: float | None,
    cfg: dict,
) -> tuple[float, dict]:
    soil = cfg["irs"]["soil"]

    if nee is None:
        c_nee = 0.5
    elif nee < -soil["nee_neutral_band"]:
        c_nee = 1.0
    elif nee <= soil["nee_neutral_band"]:
        c_nee = 0.5
    else:
        c_nee = 0.0

    r_npp = _clamp((npp or 0.0) / max(soil["npp_reference_gc_m2_year"], 1e-9))
    e_rusle = 1.0 - _clamp(erosion / max(soil["erosion_tolerance_t_ha_year"], 1e-9))
    l_leg = _clamp(legume_fraction)
    if nitrogen_balance is None:
        b_n = 0.5
    elif nitrogen_balance >= 0:
        b_n = 1.0
    elif nitrogen_balance > -soil["nitrogen_deficit_soft_kg_ha"]:
        b_n = 0.5
    else:
        b_n = 0.0

    value = 100.0 * (
        soil["nee_weight"] * c_nee
        + soil["npp_weight"] * r_npp
        + soil["erosion_weight"] * e_rusle
        + soil["legume_weight"] * l_leg
        + soil["nitrogen_weight"] * b_n
    )
    return value, {"nee": c_nee, "npp": r_npp, "erosion": e_rusle, "legume": l_leg, "nitrogen": b_n}


def shannon_diversity(families: list[str], max_crops: int = 4) -> tuple[float, float]:
    n = max(len(families), 1)
    counts: dict[str, int] = {}
    for f in families:
        counts[f] = counts.get(f, 0) + 1
    h = 0.0
    for c in counts.values():
        p = c / n
        h -= p * math.log(p)
    normaliser = math.log(max(max_crops, 2))
    return (100.0 * h / normaliser if normaliser > 0 else 0.0), h


def hazard_index(expected_loss: float) -> float:
    return 100.0 * (1.0 - _clamp(expected_loss))


def composite(components: dict[str, float], weights: dict[str, float]) -> dict:
    total = 0.0
    contributions = {}
    for key, w in weights.items():
        value = float(components.get(key, 0.0))
        contribution = w * value
        contributions[key] = round(contribution, 2)
        total += contribution
    return {
        "value": round(total, 1),
        "components": {k: round(float(v), 1) for k, v in components.items()},
        "weights": weights,
        "contributions": contributions,
    }


def label(value: float) -> tuple[str, str, str]:
    """(code, english label, english description)."""
    if value >= 80:
        return "highly_resilient", "Highly resilient", "Holds up across most of the futures tested."
    if value >= 60:
        return "resilient", "Resilient", "Holds up in most scenarios; water or diversity are the weak points."
    if value >= 40:
        return "vulnerable", "Vulnerable", "Works in normal years; loses production in bad ones."
    if value >= 20:
        return "highly_vulnerable", "Highly vulnerable", "High chance of failure under drought or heat."
    return "critical", "Critical", "This system is not sustainable under the scenarios tested."
