"""RUSLE soil erosion (spec 10.12.6).

A = R * K * LS * C * P

The R factor uses the monthly modified Fournier approximation because the demo
fixtures do not include IMERG 30-minute data; when P05 is available the caller
passes the EI30-based R and this proxy is skipped.
"""

from __future__ import annotations

import numpy as np

ENGLISH_TO_SI = 17.02  # R factor: (ft-tonf-in)/(ac-h-yr) -> MJ*mm/(ha*h*yr)
K_TO_SI = 0.1317  # K factor: US customary -> SI


def r_factor_monthly(pr_daily: np.ndarray, month: np.ndarray) -> np.ndarray:
    """Monthly R factor (SI) from daily precipitation (Renard & Freimund)."""
    pr = np.asarray(pr_daily, float)
    month = np.asarray(month, int)
    annual = float(np.sum(pr))
    out = np.zeros(12, float)
    if annual <= 0:
        return out
    for m in range(1, 13):
        pm = float(np.sum(pr[month == m]))
        if pm <= 0:
            continue
        ratio = (pm * pm) / annual
        r_english = 1.735 * (10.0 ** (1.5 * np.log10(max(ratio, 1e-9)) - 0.8188))
        out[m - 1] = max(0.0, r_english * ENGLISH_TO_SI)
    return out


def ls_factor(slope_pct: float, slope_length_m: float = 30.0) -> float:
    """Slope length-steepness factor (Wischmeier & Smith)."""
    theta = np.arctan(max(slope_pct, 0.0) / 100.0)
    sin_t = float(np.sin(theta))
    if slope_pct < 9.0:
        s = 10.8 * sin_t + 0.03
    else:
        s = 16.8 * sin_t - 0.50
    l = (max(slope_length_m, 1.0) / 22.13) ** 0.5
    return max(0.0, l * s)


def c_factor(crop_ids: list[str], families: list[str]) -> float:
    """Cover-management factor from the rotation composition."""
    if not crop_ids:
        return 0.25
    values = []
    for cid, fam in zip(crop_ids, families):
        if cid == "fallow":
            values.append(0.45)
        elif cid == "cereal_rye":
            values.append(0.05)
        elif fam == "poaceae":
            values.append(0.15)
        else:
            values.append(0.25)
    return float(np.mean(values))


def rusle(r_si: float, k_us: float, ls: float, c: float, p: float = 1.0) -> float:
    """Soil loss in t/ha/yr."""
    k_si = max(k_us, 0.0) * K_TO_SI
    return max(0.0, r_si * k_si * ls * c * p)
