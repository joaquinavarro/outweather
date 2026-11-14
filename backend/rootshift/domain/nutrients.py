"""Nutrient balance (spec 10.8).

Removal from harvested yield, nitrogen fixation credit from legumes, and the
balance against declared inputs. Never recommends a fertilizer rate.
"""

from __future__ import annotations

import math


def _coefficients(coefficients: dict, crop_id: str) -> dict:
    return coefficients.get(crop_id, {})


def rotation_nutrients(
    sequence: list[dict],
    yields_t_ha: list[float],
    areas_ha: list[float],
    coefficients: dict,
) -> dict:
    """N-P-K removal, fixation credit and balance for one rotation path.

    `sequence` items must expose `crop_id`; `yields_t_ha` are per season means.
    """
    n_rem = p_rem = k_rem = fix = 0.0
    for item, y, area in zip(sequence, yields_t_ha, areas_ha):
        coef = _coefficients(coefficients, item["crop_id"])
        if not coef:
            continue
        n_rem += y * area * coef["n_removal_kg_per_t"] / max(area, 1e-9)
        p_rem += y * area * coef["p2o5_removal_kg_per_t"] / max(area, 1e-9)
        k_rem += y * area * coef["k2o_removal_kg_per_t"] / max(area, 1e-9)
        fix += coef.get("n_fixation_kg_per_ha", 0.0)

    n_seasons = max(len(sequence), 1)
    return {
        "n_removal_kg_ha": round(n_rem / n_seasons, 1),
        "p2o5_removal_kg_ha": round(p_rem / n_seasons, 1),
        "k2o_removal_kg_ha": round(k_rem / n_seasons, 1),
        "n_fixation_kg_ha": round(fix / n_seasons, 1),
    }


def balance(removal: dict, inputs: dict | None) -> dict:
    """Apply declared inputs. Without inputs only removal is reported."""
    inputs = inputs or {}
    n_in = float(inputs.get("n_kg_ha", 0.0) or 0.0)
    p_in = float(inputs.get("p2o5_kg_ha", 0.0) or 0.0)
    k_in = float(inputs.get("k2o_kg_ha", 0.0) or 0.0)

    n_balance = n_in + removal["n_fixation_kg_ha"] - removal["n_removal_kg_ha"]
    p_balance = p_in - removal["p2o5_removal_kg_ha"]
    k_balance = k_in - removal["k2o_removal_kg_ha"]

    def status(value, soft=20.0):
        if value >= 0:
            return "balanced"
        if value > -soft:
            return "slight deficit"
        return "deficit"

    return {
        **removal,
        "n_input_kg_ha": n_in,
        "p2o5_input_kg_ha": p_in,
        "k2o_input_kg_ha": k_in,
        "n_balance_kg_ha": round(n_balance, 1),
        "p2o5_balance_kg_ha": round(p_balance, 1),
        "k2o_balance_kg_ha": round(k_balance, 1),
        "n_status": status(n_balance),
        "p_status": status(p_balance),
        "k_status": status(k_balance),
        "inputs_declared": bool(inputs),
    }


def nitrogen_score(n_balance: float, soft: float = 20.0) -> float:
    """Normalised 0-1 score used by the soil sub-index."""
    if n_balance >= 0:
        return 1.0
    if n_balance > -soft:
        return 0.5
    return 0.0
