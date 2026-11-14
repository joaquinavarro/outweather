"""Build the parcel agro-climatic context (spec 10.2-10.6).

One computation per parcel; F1-F5 consume it. Works from an offline fixture
(demo mode) or from live providers (live mode).
"""

from __future__ import annotations

import json
import math
from functools import lru_cache

import numpy as np

from .. import catalog, config
from ..domain import climate, disease as disease_mod, drought, erosion, scenarios, water
from ..domain import yield_model as ym
from ..providers import base as provider_base

CACHE: dict[str, dict] = {}
FIXTURE_REGISTRY: dict[str, dict] = {}


def register_fixture(key: str, fixture: dict) -> None:
    """Fixtures built on the fly (custom fields) live in memory for the session."""
    FIXTURE_REGISTRY[key] = fixture


# --------------------------------------------------------------------------
# IMERG monthly (P04) — real precipitation from NASA GPM
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _imerg_payload() -> dict | None:
    path = config.FIXTURES_DIR / "imerg_monthly.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def imerg_series(farm_id: str) -> dict[str, float] | None:
    """{'YYYY-MM': mm} for a farm, if the IMERG precompute covers it."""
    payload = _imerg_payload()
    if not payload:
        return None
    entry = (payload.get("farms") or {}).get(farm_id)
    if not entry:
        return None
    pairs = [(m, v) for m, v in zip(payload["months"], entry["mm"]) if v is not None]
    if len(pairs) < 0.8 * len(payload["months"]):
        return None
    return dict(pairs)


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

@lru_cache(maxsize=16)
def _load_fixture_from_disk(farm_id: str) -> dict | None:
    path = config.FIXTURES_DIR / f"{farm_id}.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_fixture(farm_id: str) -> dict | None:
    if farm_id in FIXTURE_REGISTRY:
        return FIXTURE_REGISTRY[farm_id]
    return _load_fixture_from_disk(farm_id)


def available_demo_farms() -> list[dict]:
    out = []
    for reg in catalog.regions().values():
        for farm in reg.demo_farms:
            path = config.FIXTURES_DIR / f"{farm.id}.json"
            if not path.exists():
                continue
            try:
                fixture = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                fixture = {}
            farm_meta = fixture.get("farm", {})
            out.append(
                {
                    "id": farm.id,
                    "name": farm.name,
                    "label": farm.label,
                    "county": farm.county,
                    "region_id": farm.region_id,
                    "location": farm_meta.get("location") or farm.location,
                    "boundary": farm_meta.get("boundary"),
                    "area_ha": farm_meta.get("area_ha"),
                    "irrigation": farm_meta.get("irrigation"),
                    "current_crops": farm_meta.get("current_crops"),
                }
            )
    return out


def _arrays(fixture: dict) -> dict:
    w = fixture["weather"]
    dates = w["dates"]
    ts = [
        (int(d[:4]), int(d[4:6]), int(d[6:]))
        for d in dates
    ]
    return {
        "date": np.array(dates),
        "year": np.array([t[0] for t in ts]),
        "month": np.array([t[1] for t in ts]),
        "doy": np.array(
            [
                __import__("datetime").date(t[0], t[1], t[2]).timetuple().tm_yday
                for t in ts
            ]
        ),
        "tmax": np.array(w["tmax"], float),
        "tmin": np.array(w["tmin"], float),
        "tdew": np.array(w["tdew"], float),
        "rh": np.array(w["rh"], float),
        "ws": np.array(w["ws"], float),
        "rs": np.array(w["rs"], float),
        "ps": np.array(w["ps"], float),
        "pr": np.nan_to_num(np.array(w["pr"], float), nan=0.0),
        "et0": np.array(w["et0"], float),
        "cell": w.get("cell", {}),
    }


def _season_mask(year: np.ndarray, doy: np.ndarray, y: int, sow: int, length: int) -> np.ndarray:
    end = sow + length
    if end <= 366:
        return (year == y) & (doy >= sow) & (doy < end)
    return ((year == y - 1) & (doy >= sow)) | ((year == y) & (doy < end - 366))


def _monthly(arrays: dict, years: list[int]) -> dict:
    year = arrays["year"]
    month = arrays["month"]
    mask = np.isin(year, years)
    out = {"year": [], "month": [], "pr": [], "et0": [], "pet": []}
    for y in years:
        for m in range(1, 13):
            sel = mask & (year == y) & (month == m)
            if not sel.any():
                continue
            out["year"].append(y)
            out["month"].append(m)
            out["pr"].append(float(np.sum(arrays["pr"][sel])))
            out["et0"].append(float(np.sum(arrays["et0"][sel])))
            out["pet"].append(float(np.sum(arrays["et0"][sel])))
    return {k: np.array(v) for k, v in out.items()}


def _crop_matrix(arrays: dict, soil: dict, years: list[int], pe_daily: np.ndarray, irrigated: bool, supply_mm: float) -> dict:
    year = arrays["year"]
    doy = arrays["doy"]
    et0 = arrays["et0"]
    pr = arrays["pr"]
    tmax = arrays["tmax"]
    tmin = arrays["tmin"]

    zr_default = 1.5
    taw = water.taw_mm(soil["theta_fc"], soil["theta_wp"], zr_default)

    matrix = {}
    for crop_id, crop in catalog.crops().items():
        sow = crop.sow_doy()
        length = crop.season_length_days
        kc_curve = water.kc_curve(crop.stage_days, crop.kc, length)
        rows = {"years": [], "yield_rel": [], "rho": [], "nir_mm": [], "hse": [], "fse": [], "et_ratio": []}
        for y in years:
            mask = _season_mask(year, doy, y, sow, length)
            if int(np.sum(mask)) < length * 0.8:
                continue
            idx = np.where(mask)[0]
            kc = np.resize(kc_curve, idx.size)
            bal = water.water_balance(pr[idx], et0[idx], kc, taw, crop.p_depletion, 0.5 * taw)
            etm = bal["etm"]
            rho = ym.rho_et(bal["eta_total"], etm)

            flow_start = sow + int(length * 0.5)
            if crop.flowering_window_days > 0:
                fmask = climate.window_mask(doy[idx], flow_start, max(crop.flowering_window_days, 1))
            else:
                # forage/perennial crops with no single flowering window: heat
                # stress accumulates across the whole growing season.
                fmask = np.ones(idx.size, bool)
            hse = climate.heat_stress_exposure(tmax[idx], crop.t_heat_critical_c, fmask)
            fse = climate.frost_stress_exposure(tmin[idx], crop.t_frost_critical_c, fmask)

            water_rel = ym.water_limited_ratio(crop.ky, rho)
            fh = ym.heat_factor(hse, crop.hse_ref)
            ff = ym.frost_factor(fse, crop.fse_ref)
            yrel = max(0.0, min(1.0, water_rel * fh * ff))

            nir = float(np.sum(water.net_irrigation_requirement(kc * et0[idx], pe_daily[idx])))
            if irrigated:
                deficit = max(0.0, etm - bal["eta_total"])
                covered = min(deficit, max(supply_mm, 0.0))
                rho_irr = ym.rho_et(bal["eta_total"] + covered, etm)
                yrel_irr = max(0.0, min(1.0, ym.water_limited_ratio(crop.ky, rho_irr) * fh * ff))
                rho, yrel = rho_irr, yrel_irr

            rows["years"].append(y)
            rows["yield_rel"].append(round(float(yrel), 4))
            rows["rho"].append(round(float(rho), 4))
            rows["nir_mm"].append(round(nir, 1))
            rows["hse"].append(round(float(hse), 1))
            rows["fse"].append(round(float(fse), 1))
            rows["et_ratio"].append(round(float(rho), 4))

        rows["ym_t_ha"] = float(_ym_for(crop_id))
        matrix[crop_id] = rows
    return matrix


def _ym_for(crop_id: str) -> float:
    """Attainable yield (t/ha). GAEZ in production; regional table for the demo."""
    return {
        "corn": 12.5,
        "soybean": 3.8,
        "winter_wheat": 5.2,
        "grain_sorghum": 6.5,
        "alfalfa": 11.0,
        "oats": 4.2,
        "sunflower": 2.6,
        "canola": 2.8,
        "cereal_rye": 3.0,
    }.get(crop_id, 4.0)


def _disease_matrix(arrays: dict, years: list[int]) -> dict:
    year = arrays["year"]
    doy = arrays["doy"]
    tmean = 0.5 * (arrays["tmax"] + arrays["tmin"])
    lwd = disease_mod.lwd_proxy(arrays["rh"], arrays["tmin"], arrays["tdew"], arrays["pr"])

    out: dict[str, dict] = {}
    for crop_id, crop in catalog.crops().items():
        per_crop = {}
        for dis in catalog.diseases_for(crop_id):
            sow = crop.sow_doy()
            length = crop.season_length_days
            values = []
            for y in years:
                mask = _season_mask(year, doy, y, sow, length)
                if not mask.any():
                    continue
                fi_daily = disease_mod.favorability(tmean[mask], lwd[mask], dis["cardinal_temp"], dis["wetness_hours_required"])
                values.append(disease_mod.disease_index(fi_daily, weight=dis.get("severity_weight", 1.0)))
            if values:
                per_crop[dis["id"]] = {
                    "mean_index": round(float(np.mean(values)), 1),
                    "max_index": round(float(np.max(values)), 1),
                    "by_year": [round(float(v), 1) for v in values],
                    "level": disease_mod.level(float(np.mean(values))),
                    "name": dis["name_en"],
                }
        out[crop_id] = per_crop
    return out


def _confidence(parts: dict) -> tuple[int, list[str], list[str]]:
    """(value, english caveats, caveat codes) — the codes let the UI localise them."""
    caveats: list[str] = []
    codes: list[str] = []
    factor = 1.0
    if parts["soil_source"] in ("STATSGO2", "default"):
        factor *= 0.75 if parts["soil_source"] == "STATSGO2" else 0.6
        caveats.append("Soil from a regional survey or default profile; local variability is not represented.")
        codes.append("SOIL_REGIONAL")
    if parts["synthetic"]:
        factor *= 0.85
    if parts["years"] < 24:
        factor *= 0.9
        caveats.append(f"Short climate series ({parts['years']} years): percentiles are fragile.")
        codes.append("SHORT_SERIES")
    if parts.get("pr_source") == "imerg":
        caveats.append(
            "Monthly precipitation comes from GPM IMERG (real); daily extremes "
            "(Rx1day, dry spells) still come from POWER."
        )
        codes.append("PRECIP_MIXED")
    value = int(round(100 * factor * min(1.0, parts["years"] / 24) ** 0.5))
    return max(20, min(100, value)), caveats, codes


# --------------------------------------------------------------------------
# public
# --------------------------------------------------------------------------

def build_context(fixture: dict, profile: dict | None = None) -> dict:
    farm = fixture["farm"]
    region = catalog.region(farm.get("region_id", "us_ks"))
    cache_key = farm["id"] + ":" + str(profile.get("objective") if profile else "")
    if cache_key in CACHE:
        return CACHE[cache_key]

    arrays = _arrays(fixture)
    years = list(range(config.SIM_START, config.SIM_END + 1))

    pe_daily = water.daily_effective_rain(arrays["pr"], arrays["year"], arrays["month"])

    soil = fixture["soil"]
    irrigation = farm.get("irrigation", {})
    area_ha = float(farm["area_ha"])
    irrigated = irrigation.get("status") == "irrigated"
    limit = float(irrigation.get("annual_limit_m3") or 0.0)
    supply_mm = (limit * 1000.0 / (area_ha * 10.0)) if (irrigated and limit > 0 and area_ha > 0) else 0.0

    crop_matrix = _crop_matrix(arrays, soil, years, pe_daily, irrigated, supply_mm)
    diseases = _disease_matrix(arrays, years)

    monthly = _monthly(arrays, years)

    # Precipitation source: IMERG monthly is primary (spec 7.4), POWER is the fallback.
    pr_source = "power"
    imerg_map = imerg_series(farm["id"])
    if imerg_map:
        keys = [f"{int(y)}-{int(m):02d}" for y, m in zip(monthly["year"], monthly["month"])]
        series = np.array([imerg_map.get(k, np.nan) for k in keys], float)
        if np.isfinite(series).mean() >= 0.8:
            missing = ~np.isfinite(series)
            if missing.any():
                idx = np.arange(series.size)
                series[missing] = np.interp(idx[missing], idx[~missing], series[~missing])
            monthly["pr"] = series
            pr_source = "imerg"

    spi3 = drought.spi(monthly["pr"], 3)
    spi12 = drought.spi(monthly["pr"], 12)
    spei3 = drought.spei(monthly["pr"], monthly["pet"], 3)
    spei12 = drought.spei(monthly["pr"], monthly["pet"], 12)

    spei12_by_year = {}
    for i, y in enumerate(monthly["year"]):
        if monthly["month"][i] == 12 or y not in spei12_by_year:
            spei12_by_year[int(y)] = float(spei12[i]) if np.isfinite(spei12[i]) else 0.0
    current_spei3 = float(spei3[-1]) if spei3.size and np.isfinite(spei3[-1]) else 0.0

    pools = scenarios.build_pools(years, spei12_by_year)

    rx1day = {}
    frost_years = {}
    heat_years = {}
    wind_years = {}
    runoff = fixture["synthetic"].get("runoff_mm_year", {})
    for y in years:
        mask = arrays["year"] == y
        if not mask.any():
            continue
        rx1day[y] = float(np.max(arrays["pr"][mask]))
        spring = mask & (arrays["doy"] >= 120) & (arrays["doy"] <= 160)
        frost_years[y] = bool(np.any(arrays["tmin"][spring] < 0.0))
        summer = mask & (arrays["doy"] >= 150) & (arrays["doy"] <= 250)
        heat_years[y] = bool(np.any(arrays["tmax"][summer] > 40.0))
        wind_years[y] = bool(np.any(arrays["ws"][mask] > 9.0))

    rep_year = years[-1]
    rep_mask = arrays["year"] == rep_year
    r_month = erosion.r_factor_monthly(arrays["pr"][rep_mask], arrays["month"][rep_mask])
    r_annual = float(np.sum(r_month))
    ls = erosion.ls_factor(float(soil.get("slope_pct", 2.0)))
    current_ids = [c["crop_id"] for c in farm["current_crops"]]
    current_fams = [catalog.crop(c).family for c in current_ids if c in catalog.crops()]
    c_fac = erosion.c_factor(current_ids, current_fams)
    a_loss = erosion.rusle(r_annual, float(soil.get("k_factor", 0.37)), ls, c_fac)

    sm = np.array(fixture["synthetic"]["sm_rz"], float)
    ndvi = np.array(fixture["synthetic"]["ndvi_daily"], float)
    lst_night = np.array(fixture["synthetic"]["lst_night_c"], float)

    ndvi_base_mask = arrays["year"] <= 2020
    vci_series = drought.vci(ndvi, ndvi_base_mask)

    nee = fixture["synthetic"].get("nee_gc_m2_year", {})
    npp = fixture["synthetic"].get("npp_gc_m2_year", {})
    nee_mean = float(np.mean([v for v in nee.values()])) if nee else None
    npp_mean = float(np.mean([v for v in npp.values()])) if npp else None

    # seasonal ADD for the primary crop of the farm
    primary = current_ids[0] if current_ids else "corn"
    crop = catalog.crop(primary)
    crop_mask = _season_mask(arrays["year"], arrays["doy"], years[-1], crop.sow_doy(), crop.season_length_days)
    add_days, sm_pct = drought.agricultural_drought_days(sm, arrays["year"], arrays["doy"], crop_mask)
    current_sm_pct = float(sm_pct[crop_mask][-1]) if crop_mask.any() and np.isfinite(sm_pct[crop_mask][-1]) else None

    confidence, caveats, caveat_codes = _confidence(
        {
            "soil_source": soil.get("source", "default"),
            "synthetic": bool(fixture.get("synthetic", {}).get("synthetic")),
            "years": len(years),
            "pr_source": pr_source,
        }
    )

    normals_mask = (arrays["year"] >= config.NORMALS_START) & (arrays["year"] <= config.NORMALS_END)
    annual_pr = {}
    if pr_source == "imerg":
        for i, y in enumerate(monthly["year"]):
            annual_pr[int(y)] = annual_pr.get(int(y), 0.0) + float(monthly["pr"][i])
    else:
        for y in years:
            m = arrays["year"] == y
            annual_pr[y] = float(np.sum(arrays["pr"][m]))
    pr_vals = np.array([v for v in annual_pr.values() if v is not None], float)

    _, last_spring, _first_autumn = climate.frost_dates(arrays["tmin"], arrays["doy"], arrays["year"])

    context = {
        "farm": farm,
        "region": {
            "id": region.id,
            "name": region.name,
            "seasons_per_year": region.seasons_per_year,
        },
        "seasons_per_year": region.seasons_per_year,
        "start_year": 2026,
        "area_ha": area_ha,
        "years": years,
        "arrays": arrays,
        "monthly": monthly,
        "soil": soil,
        "crop_matrix": crop_matrix,
        "disease_matrix": diseases,
        "pools": pools,
        "gaez": fixture.get("gaez", {}),
        "scoring": catalog.scoring(),
        "simulation": catalog.scoring()["simulation"],
        "rotation_effects": catalog.rotation_effects(),
        "crops_by_id": {
            cid: {
                "id": c.id,
                "name_en": c.name_en,
                "name_es": catalog.crop_name(cid, "es-ES"),
                "family": c.family,
                "is_legume": c.is_legume,
                "stand_seasons": c.stand_seasons,
                "cover": c.cover,
            }
            for cid, c in catalog.crops().items()
        },
        "water": {
            "supply_mm": round(supply_mm, 1),
            "annual_limit_m3": limit,
            "irrigated": irrigated,
        },
        "drought": {
            "spei3": round(current_spei3, 2),
            "spei3_class": drought.classify(current_spei3),
            "spei12": round(float(spei12_by_year[max(spei12_by_year)]), 2) if spei12_by_year else None,
            "spei12_by_year": spei12_by_year,
            "add_days": add_days,
            "sm_rz_pct": round(current_sm_pct, 1) if current_sm_pct is not None else None,
            "drought_freq": round(float(np.mean([v <= -1.0 for v in spei12_by_year.values()])), 3) if spei12_by_year else 0.0,
        },
        "climate": {
            "annual_precip": {
                "p10": round(float(np.percentile(pr_vals, 10)), 0),
                "p50": round(float(np.percentile(pr_vals, 50)), 0),
                "p90": round(float(np.percentile(pr_vals, 90)), 0),
            },
            "et0_annual_mm": round(float(np.sum(arrays["et0"][normals_mask]) / 30.0), 0),
            "frost_free_days": round(float(np.nanmean(_first_autumn - last_spring)), 0) if last_spring.size else None,
            "cell": arrays.get("cell", {}),
            "aridity_index": round(float(np.mean(pr_vals) / max(np.sum(arrays["et0"][normals_mask]) / 30.0, 1e-9)), 2),
            "rx1day_mm": round(float(np.mean(list(rx1day.values()))), 0),
        },
        "carbon": {"nee": round(nee_mean, 1) if nee_mean is not None else None, "npp": round(npp_mean, 1) if npp_mean is not None else None, "sink": bool(nee_mean is not None and nee_mean < 0)},
        "groundwater": {"trend_mm_year": None, "status": "unknown"},
        "erosion": {"r_factor": round(r_annual, 0), "k": float(soil.get("k_factor", 0.37)), "ls": round(ls, 2), "c": round(c_fac, 3), "a_t_ha_year": round(a_loss, 2)},
        "ndvi": {"vci_mean": round(float(np.nanmean(vci_series)), 1) if np.isfinite(vci_series).any() else None},
        "hazard_inputs": {
            "spei12_by_year": spei12_by_year,
            "rx1day_by_year": rx1day,
            "frost_years": frost_years,
            "heat_years": heat_years,
            "wind_years": wind_years,
            "runoff_pct": 0.5,
            "slope_pct": float(soil.get("slope_pct", 2.0)),
            "hydgrp": soil.get("hydgrp", "B"),
            "erosion_t_ha_year": round(a_loss, 2),
            "erosion_tolerance": 7.0,
            "add_days": add_days,
            "drought_class": drought.classify(current_spei3),
        },
        "confidence": confidence,
        "caveats": caveats,
        "caveat_codes": caveat_codes,
        "pr_source": pr_source,
        "synthetic": bool(fixture.get("synthetic", {}).get("synthetic")),
        "data_mode": config.data_mode(),
    }
    CACHE[cache_key] = context
    return context


def provenance_for(context: dict) -> list[dict]:
    farm = context["farm"]
    synthetic = context["synthetic"]
    out = [
        provider_base.provenance(
            "P15", "T2M,T2M_MAX,T2M_MIN,T2MDEW,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PS",
            "degC, %, m/s, MJ/m2/d, kPa", "1991-2024", "0.5 deg",
            cell=context["arrays"].get("cell", {}),
        ),
        provider_base.provenance("P16", "wthirdbar_r, wfifteenbar_r, kffact, hydgrpdcd", "% , US units", "static", "SSURGO polygon",
                                 source=context["soil"].get("source")),
    ]
    if synthetic:
        for pid, var in (("P01", "sm_rootzone"), ("P06", "NDVI"),
                         ("P07", "LST_Night"), ("P09", "Npp"), ("P18", "attainable yield")):
            out.append(provider_base.provenance(pid, var, "-", "2001-2024", "fixture", synthetic=True))
    if context.get("pr_source") == "imerg":
        out.append(
            provider_base.provenance(
                "P04", "precipitation", "mm/month", "2001-2024", "0.1 deg",
                access="OPeNDAP subset", product="GPM_3IMERGM v07",
            )
        )
    return out
