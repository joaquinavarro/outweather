"""Soil water balance and irrigation demand (spec 10.3, 10.11.2).

Single-layer bucket, FAO-56. Pure functions.
"""

from __future__ import annotations

import numpy as np


def taw_mm(theta_fc: float, theta_wp: float, zr_m: float) -> float:
    """Total available water (mm)."""
    return max(0.0, 1000.0 * (theta_fc - theta_wp) * zr_m)


def ks_factor(d: float, taw: float, raw: float) -> float:
    """Water stress coefficient (FAO-56 eq. 84)."""
    if taw <= 0 or taw <= raw:
        return 0.0
    if d <= raw:
        return 1.0
    return float(np.clip((taw - d) / (taw - raw), 0.0, 1.0))


def effective_rain_monthly(p_mm: float) -> float:
    """USDA-SCS effective rainfall, monthly (spec 10.11.2)."""
    p = max(0.0, float(p_mm))
    if p <= 250.0:
        return p * (125.0 - 0.2 * p) / 125.0
    return 125.0 + 0.1 * p


def daily_effective_rain(pr: np.ndarray, year: np.ndarray, month: np.ndarray) -> np.ndarray:
    """Apportion the monthly effective rainfall to days proportionally to daily rain."""
    pr = np.asarray(pr, float)
    out = np.zeros_like(pr)
    for y, m in sorted({(int(a), int(b)) for a, b in zip(year, month)}):
        mask = (year == y) & (month == m)
        total = float(np.sum(pr[mask]))
        if total <= 0:
            continue
        pe = effective_rain_monthly(total)
        out[mask] = pr[mask] / total * pe
    return out


def kc_curve(stage_days: dict, kc: dict, n_days: int) -> np.ndarray:
    """Piecewise Kc curve: ini -> linear to mid during development -> mid -> linear to end."""
    l_ini = int(stage_days.get("ini", 25))
    l_dev = int(stage_days.get("dev", 40))
    l_mid = int(stage_days.get("mid", 50))
    l_late = int(stage_days.get("late", 25))
    total = max(l_ini + l_dev + l_mid + l_late, 1)

    if n_days != total:
        # resample the stage lengths proportionally to the requested window
        scale = n_days / total
        l_ini = max(1, int(round(l_ini * scale)))
        l_dev = max(1, int(round(l_dev * scale)))
        l_mid = max(1, int(round(l_mid * scale)))
        l_late = max(1, n_days - l_ini - l_dev - l_mid)
        total = l_ini + l_dev + l_mid + l_late

    kc_ini, kc_mid, kc_end = float(kc["ini"]), float(kc["mid"]), float(kc["end"])
    out = np.empty(total, float)
    idx = 0
    out[idx : idx + l_ini] = kc_ini
    idx += l_ini
    if l_dev > 0:
        out[idx : idx + l_dev] = np.linspace(kc_ini, kc_mid, l_dev, endpoint=False)
    idx += l_dev
    out[idx : idx + l_mid] = kc_mid
    idx += l_mid
    if l_late > 0:
        out[idx : idx + l_late] = np.linspace(kc_mid, kc_end, l_late)
    return out[:n_days]


def water_balance(
    pr_mm: np.ndarray,
    et0_mm: np.ndarray,
    kc: np.ndarray,
    taw: float,
    p_depletion: float,
    d0: float,
    irrigation_mm: np.ndarray | None = None,
    runoff_mm: np.ndarray | None = None,
) -> dict:
    """Daily root-zone water balance (FAO-56 eq. 85).

    D_i = D_{i-1} - (P - RO) - I + ETc_adj + DP
    """
    pr = np.asarray(pr_mm, float)
    et0 = np.asarray(et0_mm, float)
    kc = np.asarray(kc, float)
    n = pr.size
    irr = np.zeros(n) if irrigation_mm is None else np.asarray(irrigation_mm, float)
    ro = np.zeros(n) if runoff_mm is None else np.asarray(runoff_mm, float)

    raw = max(0.0, p_depletion * taw)
    d = float(d0)
    ks = np.zeros(n)
    eta = np.zeros(n)
    dp = np.zeros(n)
    ds = np.zeros(n)
    etc = kc * et0

    for i in range(n):
        k = ks_factor(d, taw, raw)
        e = k * etc[i]
        d = d - (pr[i] - ro[i]) - irr[i] + e
        if d < 0.0:
            dp[i] = -d
            d = 0.0
        elif d > taw:
            dp[i] = d - taw
            d = taw
        ks[i] = k
        eta[i] = e
        ds[i] = d

    return {
        "d": ds,
        "ks": ks,
        "eta": eta,
        "etc": etc,
        "dp": dp,
        "etm": float(np.sum(etc)),
        "eta_total": float(np.sum(eta)),
        "stress_days": int(np.sum(ks < 1.0)),
        "severe_days": int(np.sum(ks <= 0.0)),
    }


def net_irrigation_requirement(etc: np.ndarray, pe: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, np.asarray(etc, float) - np.asarray(pe, float))


def design_flow_l_s(nir_mm: float, area_ha: float, efficiency: float, hours: float) -> float:
    """Q [L/s] = NIR[mm] * A[ha] * 2.7778 / (eta * hours)."""
    if efficiency <= 0 or hours <= 0:
        return 0.0
    return max(0.0, nir_mm * area_ha * 2.7778 / (efficiency * hours))


def pump_power_kw(flow_l_s: float, head_m: float, pump_efficiency: float = 0.65) -> float:
    """P [kW] = 9.81 * Q[m3/s] * H[m] / eta."""
    q = max(0.0, flow_l_s) / 1000.0
    if pump_efficiency <= 0:
        return 0.0
    return 9.81 * q * head_m / pump_efficiency
