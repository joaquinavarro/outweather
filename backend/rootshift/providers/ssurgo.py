"""SSURGO / STATSGO2 soil provider (P16, P17).

Two steps against the USDA Soil Data Access REST service:
  1. spatial filter on mupolygon (works through SQL Server spatial methods),
  2. attribute join on component / chorizon / muaggatt.
Weights are exact intersection areas computed with shapely.
"""

from __future__ import annotations

import numpy as np
from shapely import wkt as shapely_wkt
from shapely.geometry import Polygon

from .base import http_json, read_cache, write_cache

SDA_URL = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"


def _rows(payload: dict) -> list[dict]:
    table = payload.get("Table") or []
    if len(table) < 2:
        return []
    cols = table[0]
    return [dict(zip(cols, row)) for row in table[1:]]


def _post(sql: str) -> dict:
    return http_json(SDA_URL, {"query": sql, "format": "JSON+COLUMNNAME"}, timeout=90)


def _texture_class(sand: float, clay: float, silt: float) -> str:
    if clay >= 40:
        return "clay"
    if sand >= 45 and clay < 20:
        return "sandy loam"
    if silt >= 50:
        return "silt loam"
    if clay >= 27:
        return "clay loam"
    return "loam"


def fetch_soil(polygon_coords: list[list[float]], areasymbol: str, use_cache: bool = True) -> dict:
    """polygon_coords is [[lon, lat], ...] (closed ring, WGS84)."""
    ring = ", ".join(f"{x:.6f} {y:.6f}" for x, y in polygon_coords)
    polygon = Polygon(polygon_coords)
    key = f"{areasymbol}:{ring}"
    if use_cache:
        cached = read_cache("soil", key)
        if cached:
            return cached

    wkt = f"POLYGON(({ring}))"
    spatial_sql = (
        "SELECT mukey, muareaacres, mupolygongeo FROM mupolygon "
        f"WHERE areasymbol = '{areasymbol}' "
        f"AND mupolygongeo.STIntersects(geometry::STGeomFromText('{wkt}', 4326)) = 1"
    )
    rows = _rows(_post(spatial_sql))
    if not rows:
        raise ValueError(f"SSURGO returned no map units for {areasymbol}")

    weights: dict[str, float] = {}
    for row in rows:
        mukey = str(row["mukey"])
        try:
            geom = shapely_wkt.loads(row["mupolygongeo"])
            area = geom.intersection(polygon).area
        except Exception:
            area = float(row.get("muareaacres") or 0.0) * 1e-5
        weights[mukey] = weights.get(mukey, 0.0) + max(area, 0.0)

    total = sum(weights.values())
    if total <= 0:
        weights = {str(r["mukey"]): float(r.get("muareaacres") or 1.0) for r in rows}
        total = sum(weights.values())

    mukeys = ",".join(f"'{m}'" for m in weights)
    attr_sql = (
        "SELECT mu.mukey, mu.muname, ma.hydgrpdcd, ma.drclassdcd, "
        "c.comppct_r, c.majcompflag, c.drainagecl, "
        "ch.hzdept_r, ch.hzdepb_r, ch.claytotal_r, ch.sandtotal_r, ch.silttotal_r, "
        "ch.om_r, ch.ph1to1h2o_r, ch.cec7_r, ch.ksat_r, ch.kffact, ch.awc_r, "
        "ch.wthirdbar_r, ch.wfifteenbar_r "
        "FROM mapunit mu "
        "JOIN component c ON c.mukey = mu.mukey "
        "LEFT JOIN muaggatt ma ON ma.mukey = mu.mukey "
        "LEFT JOIN chorizon ch ON ch.cokey = c.cokey "
        f"WHERE mu.mukey IN ({mukeys}) AND c.comppct_r >= 15 "
        "ORDER BY mu.mukey, c.comppct_r DESC, ch.hzdept_r"
    )
    attrs = _rows(_post(attr_sql))
    slope_available = False
    if not attrs:
        raise ValueError("SSURGO returned no components")

    per_mukey: dict[str, list[dict]] = {}
    for row in attrs:
        per_mukey.setdefault(str(row["mukey"]), []).append(row)

    agg = {"theta_fc": 0.0, "theta_wp": 0.0, "awc_mm": 0.0, "k_factor": 0.0,
           "sand": 0.0, "clay": 0.0, "silt": 0.0, "om": 0.0, "ph": 0.0, "cec": 0.0,
           "slope": 0.0, "hydgrp": "B", "drainagecl": "well drained", "muname": ""}

    for mukey, mrows in per_mukey.items():
        w = weights.get(mukey, 0.0) / total
        if w <= 0:
            continue
        dominant = mrows[0]
        agg["muname"] = agg["muname"] or dominant.get("muname", "")
        agg["hydgrp"] = dominant.get("hydgrpdcd") or agg["hydgrp"]
        agg["drainagecl"] = dominant.get("drainagecl") or agg["drainagecl"]
        if slope_available and dominant.get("slope") not in (None, ""):
            try:
                agg["slope"] += w * float(dominant["slope"])
            except ValueError:
                pass

        horizons = [r for r in mrows if r.get("hzdept_r") not in (None, "")]
        thick_total = 0.0
        for h in horizons:
            top = max(0.0, float(h["hzdept_r"]))
            bottom = min(100.0, float(h["hzdepb_r"]))
            thick = max(0.0, bottom - top)
            if thick <= 0:
                continue
            thick_total += thick
            for src, dst in (("wthirdbar_r", "theta_fc"), ("wfifteenbar_r", "theta_wp"),
                             ("sandtotal_r", "sand"), ("claytotal_r", "clay"), ("silttotal_r", "silt"),
                             ("om_r", "om"), ("ph1to1h2o_r", "ph"), ("cec7_r", "cec")):
                val = h.get(src)
                if val not in (None, ""):
                    divisor = 100.0 if src in ("wthirdbar_r", "wfifteenbar_r") else 1.0
                    agg[dst] += w * (thick / 100.0) * (float(val) / divisor)
            if h.get("awc_r") not in (None, ""):
                agg["awc_mm"] += w * thick * float(h["awc_r"]) * 10.0
            if h.get("kffact") not in (None, ""):
                agg["k_factor"] += w * (thick / 100.0) * float(h["kffact"])
        if thick_total == 0:
            agg["awc_mm"] += w * 150.0

    agg["theta_fc"] = round(agg["theta_fc"] or 0.30, 4)
    agg["theta_wp"] = round(agg["theta_wp"] or 0.14, 4)
    agg["k_factor"] = round(agg["k_factor"] or 0.35, 4)
    agg["slope"] = round(agg["slope"] or 1.5, 2)
    agg["texture_class"] = _texture_class(agg["sand"], agg["clay"], agg["silt"])

    result = {
        "source": "SSURGO",
        "areasymbol": areasymbol,
        "mukeys": sorted(weights.keys()),
        "muname": agg["muname"],
        "theta_fc": agg["theta_fc"],
        "theta_wp": agg["theta_wp"],
        "awc_mm": round(agg["awc_mm"], 1),
        "texture_class": agg["texture_class"],
        "sand_pct": round(agg["sand"], 1),
        "clay_pct": round(agg["clay"], 1),
        "silt_pct": round(agg["silt"], 1),
        "om_pct": round(agg["om"], 2),
        "ph": round(agg["ph"], 2),
        "cec": round(agg["cec"], 2),
        "hydgrp": agg["hydgrp"],
        "drainagecl": agg["drainagecl"],
        "k_factor": agg["k_factor"],
        "slope_pct": agg["slope"],
        "n_components": len(attrs),
    }
    if use_cache:
        write_cache("soil", key, result)
    return result


def default_soil() -> dict:
    """Last-resort profile when SSURGO and STATSGO2 both fail."""
    return {
        "source": "default",
        "areasymbol": None,
        "mukeys": [],
        "muname": "default silt loam",
        "theta_fc": 0.31,
        "theta_wp": 0.14,
        "awc_mm": 170.0,
        "texture_class": "silt loam",
        "sand_pct": 20.0,
        "clay_pct": 22.0,
        "silt_pct": 58.0,
        "om_pct": 2.0,
        "ph": 6.6,
        "cec": 16.0,
        "hydgrp": "B",
        "drainagecl": "well drained",
        "k_factor": 0.37,
        "slope_pct": 2.0,
        "n_components": 0,
    }
