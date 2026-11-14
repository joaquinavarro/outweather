"""Disease favour-ability model (spec 10.10).

No diagnosis, no prescriptions. Estimates climate-driven risk for a
crop-disease pair inside a season window.
"""

from __future__ import annotations

import numpy as np


def lwd_proxy(rh, tmin, tdew, pr, lst_night=None) -> np.ndarray:
    """Daily leaf-wetness duration proxy in hours (0-24).

    Uses the daily approximation of spec 10.10.2 because POWER hourly is not in
    the project catalog. The MODIS night LST term compensates for missing hourly
    data on clear nights.
    """
    rh = np.asarray(rh, float)
    tmin = np.asarray(tmin, float)
    tdew = np.asarray(tdew, float)
    pr = np.asarray(pr, float)
    # Dew duration decays with the Tmin - Tdew gap; RH gives a second signal.
    dew_gap = np.maximum(tmin - tdew, 0.0)
    hours = 12.0 * np.exp(-dew_gap / 2.0) * np.clip((rh - 50.0) / 45.0, 0.0, 1.0)
    hours += 2.0 * (pr > 1.0).astype(float)
    if lst_night is not None:
        hours += 2.0 * (np.asarray(lst_night, float) <= tdew).astype(float)
    return np.clip(hours, 0.0, 24.0)


def _trapezoid(t: float, lo: float, opt_lo: float, opt_hi: float, hi: float) -> float:
    if t <= lo or t >= hi:
        return 0.0
    if t < opt_lo:
        return (t - lo) / max(opt_lo - lo, 1e-9)
    if t <= opt_hi:
        return 1.0
    return (hi - t) / max(hi - opt_hi, 1e-9)


def favorability(tmean: np.ndarray, lwd: np.ndarray, cardinal: dict, wetness_required: float) -> np.ndarray:
    tmean = np.asarray(tmean, float)
    g_t = np.array(
        [_trapezoid(t, cardinal["min"], cardinal["opt_lo"], cardinal["opt_hi"], cardinal["max"]) for t in tmean]
    )
    g_w = np.clip(np.asarray(lwd, float) / max(wetness_required, 1e-9), 0.0, 1.0)
    return g_t * g_w


def disease_index(daily_fi: np.ndarray, inoculum: float = 0.6, lam: float = 0.03, weight: float = 1.0) -> float:
    """Seasonal 0-100 risk index from daily favour-ability values."""
    total = float(np.sum(np.asarray(daily_fi, float) * inoculum))
    if total <= 0:
        return 0.0
    return float(min(100.0, 100.0 * (1.0 - np.exp(-lam * total)) * weight))


def level(value: float) -> str:
    if value < 25:
        return "low"
    if value < 50:
        return "medium"
    if value < 75:
        return "high"
    return "very high"


def inoculum_factor(previous_host_parcel: bool = True) -> float:
    return 1.0 if previous_host_parcel else 0.6
