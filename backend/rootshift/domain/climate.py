"""Meteorological base indicators (spec 10.2).

Pure functions: numpy arrays in, numpy arrays out. No I/O, no globals.
"""

from __future__ import annotations

import numpy as np

GSC = 0.0820  # MJ m-2 min-1
SIGMA = 4.903e-9  # MJ K-4 m-2 d-1
ALBEDO = 0.23


def ra_mj_m2_day(lat_deg: float, doy: np.ndarray) -> np.ndarray:
    """Extraterrestrial radiation (FAO-56 eq. 21)."""
    phi = np.radians(lat_deg)
    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi * doy / 365.0)
    decl = 0.409 * np.sin(2.0 * np.pi * doy / 365.0 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(decl), -1.0, 1.0))
    ra = (
        (1440.0 / np.pi)
        * GSC
        * dr
        * (ws * np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.sin(ws))
    )
    return np.maximum(ra, 0.0)


def esat(t: np.ndarray) -> np.ndarray:
    """Saturation vapour pressure (kPa)."""
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def eto_fao56(
    tmax: np.ndarray,
    tmin: np.ndarray,
    tdew: np.ndarray,
    rs: np.ndarray,
    ws2: np.ndarray,
    ps: np.ndarray,
    lat_deg: float,
    doy: np.ndarray,
    elev_m: float = 300.0,
) -> np.ndarray:
    """FAO-56 Penman-Monteith reference evapotranspiration (mm/day).

    `rs` is incoming shortwave radiation (MJ m-2 d-1) from POWER
    ALLSKY_SFC_SW_DWN. `ws2` is wind at 2 m (POWER already provides it at 2 m;
    do NOT apply the 10 m logarithmic correction).
    """
    tmax = np.asarray(tmax, float)
    tmin = np.asarray(tmin, float)
    tdew = np.asarray(tdew, float)
    rs = np.asarray(rs, float)
    ws2 = np.asarray(ws2, float)
    ps = np.asarray(ps, float)

    t = 0.5 * (tmax + tmin)
    es = 0.5 * (esat(tmax) + esat(tmin))
    ea = esat(tdew)
    delta = 4098.0 * esat(t) / (t + 237.3) ** 2
    gamma = 0.000665 * ps

    ra = ra_mj_m2_day(lat_deg, doy)
    rso = (0.75 + 2e-5 * elev_m) * ra
    ratio = np.clip(np.divide(rs, np.maximum(rso, 1e-6)), 0.0, 1.0)

    rns = (1.0 - ALBEDO) * rs
    rnl = (
        SIGMA
        * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2.0
        * (0.34 - 0.14 * np.sqrt(np.maximum(ea, 0.0)))
        * (1.35 * ratio - 0.35)
    )
    rn = rns - rnl

    num = 0.408 * delta * rn + gamma * (900.0 / (t + 273.0)) * ws2 * (es - ea)
    den = delta + gamma * (1.0 + 0.34 * ws2)
    return np.maximum(num / den, 0.0)


def eto_hargreaves(tmax: np.ndarray, tmin: np.ndarray, lat_deg: float, doy: np.ndarray) -> np.ndarray:
    """Fallback when radiation is missing (spec 10.2.4)."""
    ra = ra_mj_m2_day(lat_deg, doy)
    t = 0.5 * (tmax + tmin)
    return np.maximum(0.0023 * (t + 17.8) * np.sqrt(np.maximum(tmax - tmin, 0.0)) * ra, 0.0)


def gdd_daily(
    tmax: np.ndarray, tmin: np.ndarray, base_c: float, opt_c: float | None = None
) -> np.ndarray:
    """Capped growing degree days (spec 10.2.1)."""
    tmax = np.asarray(tmax, float)
    if opt_c is not None:
        tmax = np.minimum(tmax, opt_c)
    return np.maximum(0.0, 0.5 * (tmax + np.asarray(tmin, float)) - base_c)


def vpd_daily(tmax: np.ndarray, tmin: np.ndarray, tdew: np.ndarray) -> np.ndarray:
    return np.maximum(0.5 * (esat(tmax) + esat(tmin)) - esat(tdew), 0.0)


def frost_dates(tmin: np.ndarray, doy: np.ndarray, year: np.ndarray, threshold: float = 0.0):
    """Last spring frost and first autumn frost per year, as day-of-year.

    Returns (years, last_spring_doy, first_autumn_doy) with NaN where absent.
    """
    tmin = np.asarray(tmin, float)
    years = np.unique(year)
    last_spring = np.full(years.shape, np.nan)
    first_autumn = np.full(years.shape, np.nan)
    for i, y in enumerate(years):
        mask = year == y
        spring = mask & (doy < 183) & (tmin < threshold)
        autumn = mask & (doy >= 183) & (tmin < threshold)
        if spring.any():
            last_spring[i] = float(np.max(doy[spring]))
        if autumn.any():
            first_autumn[i] = float(np.min(doy[autumn]))
    return years, last_spring, first_autumn


def window_mask(doy: np.ndarray, start: int, length: int) -> np.ndarray:
    """True for days inside a [start, start+length) day-of-year window (wraps at 366)."""
    d = np.mod(np.asarray(doy, float), 366.0)
    s = float(np.mod(start, 366))
    e = s + float(length)
    if e <= 366:
        return (d >= s) & (d < e)
    return (d >= s) | (d < (e - 366))


def heat_stress_exposure(tmax: np.ndarray, crit_c: float, mask: np.ndarray) -> float:
    return float(np.sum(np.maximum(0.0, tmax[mask] - crit_c)))


def frost_stress_exposure(tmin: np.ndarray, crit_c: float, mask: np.ndarray) -> float:
    return float(np.sum(np.maximum(0.0, crit_c - tmin[mask])))
