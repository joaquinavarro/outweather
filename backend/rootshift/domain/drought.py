"""Drought and vegetation indices (spec 10.4).

SPI uses a gamma fit on monthly precipitation (zeros handled with the
probability-of-zero correction). SPEI uses a log-logistic (Fisk) fit on the
climatic water balance D = P - PET, shifted to be strictly positive; this is a
two-parameter approximation of the three-parameter log-logistic recommended by
Vicente-Serrano et al. (2010) and is documented as such.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

_CLIP = 1e-6


def _to_z(cdf: np.ndarray) -> np.ndarray:
    return stats.norm.ppf(np.clip(cdf, _CLIP, 1.0 - _CLIP))


def standardized_index(values: np.ndarray, kind: str = "gamma") -> np.ndarray:
    """Standardised index (mean 0, sd 1) from a monthly series."""
    x = np.asarray(values, float)
    out = np.full_like(x, np.nan)
    mask = np.isfinite(x)
    xs = x[mask]
    if xs.size < 24:
        return out

    if kind == "gamma":
        zeros = xs <= 0.0
        p0 = float(np.mean(zeros))
        pos = xs[~zeros]
        if pos.size < 12:
            return out
        try:
            shape, loc, scale = stats.gamma.fit(pos, floc=0.0)
        except Exception:
            return out
        cdf = p0 + (1.0 - p0) * stats.gamma.cdf(xs, shape, loc=loc, scale=scale)
    else:
        shift = -float(np.min(xs)) + 1e-3
        pos = xs + shift
        try:
            shape, loc, scale = stats.fisk.fit(pos, floc=0.0)
        except Exception:
            return out
        cdf = stats.fisk.cdf(pos, shape, loc=loc, scale=scale)

    out[mask] = _to_z(np.asarray(cdf, float))
    return out


def rolling_sum(values: np.ndarray, window: int) -> np.ndarray:
    """Trailing rolling sum; NaN before the first full window."""
    x = np.asarray(values, float)
    out = np.full_like(x, np.nan)
    if x.size >= window:
        c = np.concatenate([[0.0], np.nancumsum(x)])
        out[window - 1 :] = c[window:] - c[:-window]
    return out


def spi(monthly_pr: np.ndarray, scale: int = 3) -> np.ndarray:
    return standardized_index(rolling_sum(monthly_pr, scale), kind="gamma")


def spei(monthly_pr: np.ndarray, monthly_pet: np.ndarray, scale: int = 3) -> np.ndarray:
    d = np.asarray(monthly_pr, float) - np.asarray(monthly_pet, float)
    return standardized_index(rolling_sum(d, scale), kind="loglogistic")


def classify(z: float) -> str:
    """Standard SPEI/SPI classification (spec 10.4.1)."""
    if not np.isfinite(z):
        return "unknown"
    if z >= 2.0:
        return "extremely wet"
    if z >= 1.5:
        return "very wet"
    if z >= 1.0:
        return "moderately wet"
    if z > -1.0:
        return "near normal"
    if z > -1.5:
        return "moderate drought"
    if z > -2.0:
        return "severe drought"
    return "extreme drought"


def _daily_matrix(values: np.ndarray, year: np.ndarray, doy: np.ndarray) -> np.ndarray:
    years = np.unique(year)
    mat = np.full((years.size, 366), np.nan)
    yindex = {int(y): i for i, y in enumerate(years)}
    for v, y, d in zip(values, year, doy):
        if np.isfinite(v) and 1 <= int(d) <= 366:
            mat[yindex[int(y)], int(d) - 1] = v
    return mat


def percentile_series(values: np.ndarray, year: np.ndarray, doy: np.ndarray, window: int = 7) -> np.ndarray:
    """Percentile (0-100) of each day within a +/-window day-of-year baseline."""
    mat = _daily_matrix(np.asarray(values, float), year, doy)
    pct_mat = np.full_like(mat, np.nan)
    for d in range(366):
        cols = [(d + k) % 366 for k in range(-window, window + 1)]
        pool = mat[:, cols].ravel()
        pool = pool[np.isfinite(pool)]
        if pool.size < 10:
            continue
        col = mat[:, d]
        ok = np.isfinite(col)
        if not ok.any():
            continue
        pct_mat[ok, d] = stats.percentileofscore(pool, col[ok], kind="rank")
    years = np.unique(year)
    yindex = {int(y): i for i, y in enumerate(years)}
    out = np.full(values.shape, np.nan, float)
    for i, (y, d) in enumerate(zip(year, doy)):
        out[i] = pct_mat[yindex[int(y)], int(d) - 1]
    return out


def agricultural_drought_days(
    sm: np.ndarray,
    year: np.ndarray,
    doy: np.ndarray,
    season_mask: np.ndarray,
    threshold: float = 20.0,
) -> tuple[int, np.ndarray]:
    """ADD: days inside the season with root-zone moisture below the threshold percentile."""
    pct = percentile_series(sm, year, doy)
    hit = np.isfinite(pct) & season_mask & (pct < threshold)
    return int(np.sum(hit)), pct


def vci(ndvi: np.ndarray, baseline_mask: np.ndarray) -> np.ndarray:
    """Vegetation Condition Index (Kogan, 1995)."""
    x = np.asarray(ndvi, float)
    base = x[baseline_mask]
    base = base[np.isfinite(base)]
    if base.size < 10:
        return np.full_like(x, np.nan)
    lo, hi = float(np.min(base)), float(np.max(base))
    if hi - lo < 1e-9:
        return np.full_like(x, np.nan)
    return np.clip((x - lo) / (hi - lo) * 100.0, 0.0, 100.0)


def return_period(series: np.ndarray, value: float) -> float:
    """Gumbel return period for a value, from annual maxima (L-moment fit)."""
    x = np.asarray(series, float)
    x = x[np.isfinite(x)]
    if x.size < 10:
        return float("nan")
    try:
        mu, beta = stats.gumbel_r.fit(x)
    except Exception:
        return float("nan")
    prob = float(stats.gumbel_r.cdf(value, mu, beta))
    prob = min(max(prob, 1e-4), 1 - 1e-6)
    return 1.0 / (1.0 - prob)
