"""Hazard assessment and field-operations windows (spec 10.12)."""

from __future__ import annotations

import numpy as np




def _p_annual(flags: list[bool]) -> float:
    if not flags:
        return float("nan")
    return float(np.mean(flags))


MAX_RETURN_PERIOD = 50.0


def _cap(t: float) -> float:
    """With 24 years of record we do not report return periods beyond 50 years."""
    if t != t:
        return t
    return round(min(t, MAX_RETURN_PERIOD), 1)


def assess(catalog: list[dict], data: dict) -> list[dict]:
    """Return one assessment per hazard in the catalog."""
    out = []
    for hz in catalog:
        hid = hz["id"]
        entry = {
            "hazard": hid,
            "name": hz["name_en"],
            "calculable": bool(hz["calculable"]),
            "source": hz["source"],
            "playbook": hz["playbook"],
        }

        if not hz["calculable"]:
            entry.update({"p_annual": None, "return_period_years": None, "susceptibility": None, "status": "insufficient data"})
            out.append(entry)
            continue

        if hid == "drought":
            flags = [v <= -1.0 for v in data.get("spei12_by_year", {}).values() if v is not None]
            p = _p_annual(flags)
            entry.update(
                {
                    "p_annual": round(p, 4) if p == p else None,
                    "return_period_years": _cap(1.0 / p) if p and p == p else None,
                    "susceptibility": data.get("add_days"),
                    "status": data.get("drought_class", "unknown"),
                }
            )

        elif hid == "flood":
            rx = data.get("rx1day_by_year", {})
            vals = np.array([v for v in rx.values() if v is not None], float)
            if vals.size >= 10:
                thr = float(np.percentile(vals, 90))
                flags = [v >= thr for v in vals]
                p = _p_annual(flags)
                t = 1.0 / p if p > 0 else float("nan")
            else:
                p, t = float("nan"), float("nan")
            slope = float(data.get("slope_pct", 1.0))
            s_slope = 1.0 - min(1.0, slope / 10.0)
            s_soil = {"A": 0.0, "B": 0.33, "C": 0.66, "D": 1.0}.get(data.get("hydgrp", "B"), 0.33)
            si = 100.0 * (0.40 * 0.9 + 0.25 * data.get("runoff_pct", 0.5) + 0.25 * s_slope + 0.10 * s_soil)
            entry.update(
                {
                    "p_annual": round(p, 4) if p == p else None,
                    "return_period_years": _cap(t) if t == t else None,
                    "susceptibility": round(si, 1),
                    "status": "high" if si >= 50 else "moderate" if si >= 25 else "low",
                }
            )

        elif hid == "frost":
            flags = list(data.get("frost_years", {}).values())
            p = _p_annual(flags)
            entry.update(
                {
                    "p_annual": round(p, 4) if p == p else None,
                    "return_period_years": _cap(1.0 / p) if p and p == p else None,
                    "susceptibility": round(p * 100, 1) if p == p else None,
                    "status": "observed",
                }
            )

        elif hid == "heat":
            flags = list(data.get("heat_years", {}).values())
            p = _p_annual(flags)
            entry.update(
                {
                    "p_annual": round(p, 4) if p == p else None,
                    "return_period_years": _cap(1.0 / p) if p and p == p else None,
                    "susceptibility": round(p * 100, 1) if p == p else None,
                    "status": "observed",
                }
            )

        elif hid == "wind":
            flags = list(data.get("wind_years", {}).values())
            p = _p_annual(flags)
            entry.update(
                {
                    "p_annual": round(p, 4) if p == p else None,
                    "return_period_years": _cap(1.0 / p) if p and p == p else None,
                    "susceptibility": round(p * 100, 1) if p == p else None,
                    "status": "observed",
                }
            )

        elif hid == "erosion":
            loss = float(data.get("erosion_t_ha_year", 0.0))
            tol = float(data.get("erosion_tolerance", 7.0))
            entry.update(
                {
                    "p_annual": None,
                    "return_period_years": None,
                    "susceptibility": round(100.0 * min(1.0, loss / max(tol, 1e-9)), 1),
                    "status": "above tolerance" if loss > tol else "within tolerance",
                    "loss_t_ha_year": round(loss, 2),
                }
            )

        out.append(entry)
    return out


def workability_windows(pr: np.ndarray, year: np.ndarray, month: np.ndarray) -> dict:
    """Windows of >= 3 consecutive days suitable for field work.

    Fallback rule (no SMAP surface moisture available): <= 5 mm in the previous
    3 days and no rain today.
    """
    pr = np.asarray(pr, float)
    wet3 = np.convolve(pr, np.ones(3), mode="full")[: pr.size]
    ok = (pr < 1.0) & (wet3 <= 5.0)

    windows = []
    i = 0
    n = ok.size
    while i < n:
        if not ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and ok[j + 1]:
            j += 1
        if j - i + 1 >= 3:
            windows.append(
                {
                    "start_doy": int(i),
                    "end_doy": int(j),
                    "days": int(j - i + 1),
                    "month": int(month[i]),
                }
            )
        i = j + 1

    by_month: dict[int, int] = {}
    for w in windows:
        by_month[w["month"]] = by_month.get(w["month"], 0) + 1
    return {"windows": windows, "windows_by_month": by_month}
