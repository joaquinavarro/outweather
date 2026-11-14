"""Application services: turn a context into the five product outputs.

F1 rotation, F2 disease, F3 irrigation, F5 hazards and the IRS live here; the
domain modules stay pure.
"""

from __future__ import annotations

import numpy as np

from .. import catalog, config
from ..domain import hazards as hazards_mod
from ..domain import irrigation as irrigation_mod
from ..domain import nutrients as nutrients_mod
from ..domain import resilience, rotation
from . import context as context_service


def _profile_from_fixture(fixture: dict) -> dict:
    farm = fixture["farm"]
    return {
        "name": farm["name"],
        "objective": "balanced",
        "risk_tolerance": "medium",
        "horizon_seasons": 8,
        "must_include": [],
        "excluded_crops": [],
        "max_crops": 4,
    }


def get_fixture(demo_id: str) -> dict:
    fixture = context_service.load_fixture(demo_id)
    if fixture is None:
        raise KeyError(f"unknown demo farm: {demo_id}")
    return fixture


def get_context(demo_id: str) -> dict:
    fixture = get_fixture(demo_id)
    return context_service.build_context(fixture, _profile_from_fixture(fixture))


# --------------------------------------------------------------------------
# F1
# --------------------------------------------------------------------------

def _viable_candidates(context: dict, profile: dict) -> list[dict]:
    excluded = set(profile.get("excluded_crops") or [])
    region_id = context["farm"].get("region_id", "us_ks")
    region = catalog.region(region_id)
    out = []
    for cid in region.crops:
        if cid in excluded:
            continue
        crop = catalog.crop(cid)
        matrix = context["crop_matrix"].get(cid)
        if not matrix or not matrix["years"]:
            continue
        out.append(
            {
                "id": cid,
                "name_en": crop.name_en,
                "family": crop.family,
                "is_legume": crop.is_legume,
                "cover": crop.cover,
                "stand_seasons": crop.stand_seasons,
            }
        )
    return out


def _legume_fraction(sequence: list[str]) -> float:
    if not sequence:
        return 0.0
    crops = catalog.crops()
    return sum(1 for c in sequence if crops[c].is_legume) / len(sequence)


def _irs(context: dict, sequence: list[str], metrics: dict, n_balance: float | None) -> dict:
    cfg = context["scoring"]
    matrix = context["crop_matrix"]
    crops = catalog.crops()

    rho_values = []
    coverage_hits = []
    for cid in sequence:
        m = matrix.get(cid)
        if not m:
            continue
        rho_values.extend(m["rho"])
        coverage_hits.extend(1 if r >= 0.7 else 0 for r in m["rho"])
    rho_mean = float(np.mean(rho_values)) if rho_values else 0.0
    coverage = float(np.mean(coverage_hits)) if coverage_hits else 0.0

    gw = context["groundwater"]
    i_water, water_parts = resilience.water_index(rho_mean, coverage, gw["status"], gw["trend_mm_year"], cfg)
    i_stab = resilience.stability_index(metrics["cv"], metrics["p_fail"], cfg)

    nee = context["carbon"]["nee"]
    npp = context["carbon"]["npp"]
    i_soil, soil_parts = resilience.soil_index(
        nee, npp, context["erosion"]["a_t_ha_year"], _legume_fraction(sequence), n_balance, cfg
    )

    families = [crops[c].family for c in sequence]
    i_div, _ = resilience.shannon_diversity(families, max_crops=4)

    fi_values = []
    for cid in sequence:
        for entry in context["disease_matrix"].get(cid, {}).values():
            fi_values.append(entry["mean_index"])
    i_health = 100.0 - (float(np.mean(fi_values)) if fi_values else 0.0)

    expected_loss = 0.0
    for hz in context.get("hazards", []):
        if not hz.get("calculable"):
            continue
        p = hz.get("p_annual")
        if p is None:
            continue
        expected_loss += 0.22 * float(p)
    i_haz = resilience.hazard_index(min(1.0, expected_loss))

    components = {
        "water": i_water,
        "stability": i_stab,
        "soil": i_soil,
        "diversity": i_div,
        "health": max(0.0, i_health),
        "hazard": i_haz,
    }
    composite = resilience.composite(components, cfg["irs"]["weights"])
    label_code, label_text, blurb = resilience.label(composite["value"])
    composite["label_code"] = label_code
    composite["label"] = label_text
    composite["description"] = blurb
    composite["parts"] = {"water": water_parts, "soil": soil_parts}
    return composite


def _findings(context: dict, sequence: list[str], metrics: dict, baseline_metrics: dict, nut: dict, scenarios: dict, baseline_scenarios: dict) -> list[dict]:
    out = []
    crops = catalog.crops()

    nir_prop = float(np.sum([np.mean(context["crop_matrix"][c]["nir_mm"]) for c in sequence if c in context["crop_matrix"]]))
    base_ids = [c["crop_id"] for c in context["farm"].get("current_crops", [])]
    if base_ids:
        nir_base = float(np.sum([np.mean(context["crop_matrix"][c]["nir_mm"]) for c in base_ids if c in context["crop_matrix"]])) or 1.0
        if nir_prop < nir_base * 0.95:
            pct = (1 - nir_prop / nir_base) * 100
            out.append(
                {
                    "code": "WATER_GAP_COVERED",
                    "severity": "positive",
                    "text": f"The proposed rotation cuts seasonal irrigation demand by {pct:.0f}% versus the current one.",
                    "params": {"pct": round(pct, 0), "current": round(nir_base, 0), "proposed": round(nir_prop, 0)},
                    "evidence": {"indicator": "seasonal_nir_mm", "current": round(nir_base, 0), "proposed": round(nir_prop, 0)},
                }
            )

    legumes = [c for c in sequence if crops[c].is_legume]
    if legumes:
        out.append(
            {
                "code": "LEGUME_BREAK",
                "severity": "positive",
                "text": f"Adds {len(legumes)} legume season(s) to the rotation, breaking the cereal disease cycle.",
                "params": {"count": len(legumes)},
                "evidence": {"rule": "R4", "count": len(legumes)},
            }
        )

    fams = [crops[c].family for c in sequence]
    longest, run = 1, 1
    for i in range(1, len(fams)):
        run = run + 1 if fams[i] == fams[i - 1] else 1
        longest = max(longest, run)
    if longest <= 1:
        out.append(
            {
                "code": "FAMILY_BREAK",
                "severity": "positive",
                "text": "No two consecutive seasons share a plant family.",
                "params": {},
                "evidence": {"rule": "R2", "longest_run": longest},
            }
        )

    prod_delta = metrics["production_index"] - baseline_metrics["production_index"]
    if abs(prod_delta) > 0.01:
        pct = prod_delta / max(baseline_metrics["production_index"], 1e-9) * 100
        out.append(
            {
                "code": "PRODUCTION_SHIFT",
                "severity": "positive" if prod_delta > 0 else "warning",
                "text": f"Relative production changes by {pct:+.1f}% versus the current rotation.",
                "params": {
                    "pct": round(pct, 1),
                    "current_index": baseline_metrics["production_index"],
                    "proposed_index": metrics["production_index"],
                },
                "evidence": {"current_index": baseline_metrics["production_index"], "proposed_index": metrics["production_index"]},
            }
        )

    if nut.get("n_balance_kg_ha", 0) < 0:
        out.append(
            {
                "code": "NUTRIENT_DEFICIT",
                "severity": "warning",
                "text": f"Nitrogen removal exceeds declared inputs plus fixation by {abs(nut['n_balance_kg_ha']):.0f} kg N/ha.",
                "params": {"deficit": round(abs(nut["n_balance_kg_ha"]), 0)},
                "evidence": {"n_balance_kg_ha": nut["n_balance_kg_ha"]},
            }
        )

    if context["carbon"]["sink"]:
        out.append(
            {
                "code": "CARBON_GAIN",
                "severity": "positive",
                "text": "The surrounding landscape is a net carbon sink over the reference period.",
                "params": {"nee": context["carbon"]["nee"]},
                "evidence": {"nee_gc_m2_year": context["carbon"]["nee"]},
            }
        )

    s2 = (scenarios or {}).get("S2")
    s2b = (baseline_scenarios or {}).get("S2")
    if s2 and s2b:
        delta = s2["production_index"] - s2b["production_index"]
        out.append(
            {
                "code": "DROUGHT_SENSITIVITY",
                "severity": "positive" if delta >= 0 else "warning",
                "text": f"Under a three-year drought the proposed rotation holds an index of {s2['production_index']:.0f} versus {s2b['production_index']:.0f} today.",
                "params": {"proposed": round(s2["production_index"], 0), "current": round(s2b["production_index"], 0)},
                "evidence": {"scenario": "S2", "proposed": s2["production_index"], "current": s2b["production_index"]},
            }
        )

    return out[:6]


def constraint_warnings(sequence: list[str]) -> list[dict]:
    """Hard-constraint violations the UI shows as warnings (it never blocks edits)."""
    crops = catalog.crops()
    out = []
    for i in range(1, len(sequence)):
        prev, cur = sequence[i - 1], sequence[i]
        if cur == prev:
            out.append(
                {
                    "code": "R3",
                    "message": f"{crops[cur].name_en} repeats in consecutive seasons.",
                    "message_es": f"{crops[cur].name_en} se repite en campañas consecutivas.",
                }
            )
        elif crops[cur].family == crops[prev].family:
            out.append(
                {
                    "code": "R2",
                    "message": f"{crops[cur].name_en} follows the same plant family ({crops[cur].family}).",
                    "message_es": f"{crops[cur].name_en} repite la familia botánica ({crops[cur].family}).",
                }
            )
    return out


def recompute_rotation(context: dict, base_result: dict, sequence: list[str]) -> dict:
    """Re-evaluate an edited sequence against the stored baseline.

    Used by PUT /rotations/{id}: the UI edits a season and needs the metrics, the
    IRS, the nutrient balance and the findings recomputed, not just the sequence.
    """
    if len(sequence) != len(base_result["sequence"]):
        raise ValueError("the edited sequence must keep the same number of seasons")

    unknown = [cid for cid in sequence if cid not in catalog.crops()]
    if unknown:
        raise ValueError(f"unknown crop ids: {unknown}")

    context["hazards"] = hazards_mod.assess(catalog.hazards(), context["hazard_inputs"])
    scenarios = rotation.evaluate_sequence(sequence, context, context["area_ha"], 400, context["simulation"]["seed"])
    metrics = scenarios["S0"]
    items = rotation.sequence_items(sequence, context, context["area_ha"], context["start_year"])

    nut = nutrients_mod.balance(
        nutrients_mod.rotation_nutrients(
            items,
            [Context_yield(context, c) for c in sequence],
            [context["area_ha"]] * len(sequence),
            catalog.nutrients(),
        ),
        context["farm"].get("resources", {}).get("fertility"),
    )

    irs = _irs(context, sequence, metrics, nut.get("n_balance_kg_ha"))
    baseline = base_result["baseline"]
    findings = _findings(context, sequence, metrics, baseline["metrics"], nut, scenarios, baseline["scenarios"])
    baseline_irs = baseline.get("irs") or {}

    return {
        "rotation_id": base_result.get("rotation_id", "rot_edited"),
        "sequence": items,
        "metrics": metrics,
        "scenarios": scenarios,
        "baseline": baseline,
        "delta": {
            "production_pct": round(
                (metrics["production_index"] - baseline["metrics"]["production_index"])
                / max(baseline["metrics"]["production_index"], 1e-9)
                * 100,
                1,
            ),
            "p_fail_delta": round(metrics["p_fail"] - baseline["metrics"]["p_fail"], 3),
            "irs_delta": round(irs["value"] - baseline_irs.get("value", 0), 1),
        },
        "irs": irs,
        "nutrients": nut,
        "findings": findings,
        "candidates": base_result.get("candidates", 0),
        "edited": True,
        "warnings": constraint_warnings(sequence),
        "provenance": context_service.provenance_for(context),
        "caveats": context["caveats"],
        "confidence": context["confidence"],
    }


def build_rotation(context: dict, profile: dict) -> dict:
    crops_catalog = catalog.crops()

    # The crop the farmer already has (None when they chose "None" in the design
    # panel); it is pinned to season one of the proposed rotation.
    first_crop = None
    current_crops = context["farm"].get("current_crops") or []
    if current_crops and current_crops[0].get("crop_id") in crops_catalog:
        first_crop = current_crops[0]["crop_id"]

    # Crops the farmer wants to plant (the "preferred" selection). They must all
    # appear in the rotation. Dedupe, drop exclusions and the pinned current crop.
    excluded = set(profile.get("excluded_crops") or [])
    must: list[str] = []
    seen: set[str] = set()
    for cid in profile.get("must_include") or []:
        if cid in crops_catalog and cid not in excluded and cid not in seen and cid != first_crop:
            must.append(cid)
            seen.add(cid)

    n_seasons = int(profile.get("horizon_seasons") or 8)
    # The horizon has to fit every selected crop; never propose what cannot fit.
    available_slots = n_seasons - (1 if first_crop else 0)
    if len(must) > available_slots:
        must = must[:available_slots]

    # The farmer's selections are a hard requirement, so raise the distinct-species
    # cap if needed instead of silently dropping a chosen crop (max 6 keeps it sane).
    required_species = len(set(must) | ({first_crop} if first_crop else set()))
    max_crops = int(profile.get("max_crops") or 4)
    max_crops = min(max(max_crops, required_species), 6)

    cons = rotation.Constraints(
        n_seasons=n_seasons,
        max_crops=max_crops,
        must_include=must,
        excluded=list(excluded),
        first_crop=first_crop,
    )

    candidates = _viable_candidates(context, profile)
    irrigated = context["water"]["irrigated"]
    water_limit = context["water"]["supply_mm"] if irrigated and context["water"]["supply_mm"] > 0 else None

    result = rotation.optimize(
        candidates,
        context,
        cons,
        context["area_ha"],
        objective_name=profile.get("objective", "balanced"),
        risk_tolerance=profile.get("risk_tolerance", "medium"),
        water_limit_mm=water_limit,
        water_norm=0.6 if irrigated else 0.4,
    )

    sequence = result["sequence"]
    items = rotation.sequence_items(sequence, context, context["area_ha"], context["start_year"])

    base_ids = rotation.baseline_sequence(current_crops, cons.n_seasons)
    if not base_ids:
        # "None" current crop: compare the proposal against the naive alternative
        # of planting a single preferred crop every season (the region default if
        # nothing was selected), so the resilience gain is still readable.
        fallback = (must[0] if must else (catalog.region(context["farm"].get("region_id", "us_ks")).crops[0]))
        base_ids = [fallback] * cons.n_seasons
    base_scen = rotation.evaluate_sequence(base_ids, context, context["area_ha"], 400, 7)
    base_items = rotation.sequence_items(base_ids, context, context["area_ha"], context["start_year"])

    yields = [Context_yield(context, c) for c in sequence]
    areas = [context["area_ha"]] * len(sequence)
    nut = nutrients_mod.balance(
        nutrients_mod.rotation_nutrients(items, yields, areas, catalog.nutrients()),
        context["farm"].get("resources", {}).get("fertility"),
    )

    # hazards are needed by the IRS
    context["hazards"] = hazards_mod.assess(catalog.hazards(), context["hazard_inputs"])

    irs = _irs(context, sequence, result["metrics"], nut.get("n_balance_kg_ha"))
    base_irs = _irs(context, base_ids, base_scen["S0"], nut.get("n_balance_kg_ha"))

    findings = _findings(context, sequence, result["metrics"], base_scen["S0"], nut, result["scenarios"], base_scen)

    return {
        "rotation_id": "rot_optimized",
        "sequence": items,
        "metrics": result["metrics"],
        "scenarios": result["scenarios"],
        "baseline": {
            "rotation_id": "rot_current",
            "sequence": base_items,
            "metrics": base_scen["S0"],
            "scenarios": base_scen,
            "irs": base_irs,
        },
        "delta": {
            "production_pct": round(
                (result["metrics"]["production_index"] - base_scen["S0"]["production_index"])
                / max(base_scen["S0"]["production_index"], 1e-9)
                * 100,
                1,
            ),
            "p_fail_delta": round(result["metrics"]["p_fail"] - base_scen["S0"]["p_fail"], 3),
            "irs_delta": round(irs["value"] - base_irs["value"], 1),
        },
        "irs": irs,
        "nutrients": nut,
        "findings": findings,
        "candidates": len(candidates),
        "provenance": context_service.provenance_for(context),
        "caveats": context["caveats"],
        "confidence": context["confidence"],
    }


def Context_yield(context: dict, crop_id: str) -> float:
    """Mean simulated yield of a crop across the historical years (t/ha)."""
    m = context["crop_matrix"].get(crop_id)
    if not m or not m["years"]:
        return 0.0
    return float(np.mean(m["yield_rel"])) * float(m["ym_t_ha"])


# --------------------------------------------------------------------------
# F2
# --------------------------------------------------------------------------

def disease_report(
    context: dict,
    crop_ids: list[str] | None = None,
    locale: str = "en-US",
    profile: dict | None = None,
) -> dict:
    available = context["disease_matrix"]
    if not crop_ids:
        # Default: every crop the farmer selected for the farm — the current crop
        # plus the preferred crops chosen in the design panel. That is the set the
        # whole simulation takes into account, so the disease panel must cover all
        # of them, not just the one current crop.
        current = [c.get("crop_id") for c in context["farm"].get("current_crops", [])]
        preferred = list((profile or {}).get("must_include") or [])
        crop_ids = [cid for cid in current + preferred if cid]
    ids: list[str] = []
    for cid in crop_ids:
        if cid in available and cid not in ids:
            ids.append(cid)
    crop_ids = ids
    crops = catalog.crops()
    out = []
    for cid in crop_ids:
        if cid not in available:
            continue
        entries = []
        for did, entry in available[cid].items():
            loc = catalog.disease_localised(did, locale)
            es = catalog.disease_localised(did, "es-ES")
            dis = next((d for d in catalog.diseases() if d["id"] == did), None)
            entries.append(
                {
                    "disease_id": did,
                    "name": loc["name"],
                    "name_en": entry["name"],
                    "name_es": es["name"],
                    "risk_index": entry["mean_index"],
                    "max_index": entry["max_index"],
                    "level": entry["level"],
                    "pathogen": dis["pathogen"] if dis else None,
                    "actions": loc["actions"],
                    "actions_es": es["actions"],
                    "confidence": "medium",
                }
            )
        if not entries:
            continue
        entries.sort(key=lambda e: e["risk_index"], reverse=True)
        out.append(
            {
                "crop_id": cid,
                "crop_name": catalog.crop_name(cid, locale) if cid in crops else cid,
                "crop_name_en": crops[cid].name_en if cid in crops else cid,
                "diseases": entries,
            }
        )
    if locale.startswith("es"):
        caveats = [
            "El mojado foliar se estima con datos diarios.",
            "Los umbrales son preliminares, pendientes de validación agronómica.",
        ]
    else:
        caveats = [
            "Leaf wetness is estimated from daily data.",
            "Thresholds are preliminary pending agronomist validation.",
        ]
    return {
        "crops": out,
        "caveats": caveats,
        "caveat_codes": ["LEAF_WETNESS_PROXY", "THRESHOLDS_PRELIMINARY"],
    }


# --------------------------------------------------------------------------
# F3
# --------------------------------------------------------------------------

def irrigation_report(context: dict, request: dict | None = None, profile: dict | None = None) -> dict:
    request = request or {}
    profile = profile or {}
    farm = context["farm"]
    irrigation = farm.get("irrigation", {})
    area_ha = float(context["area_ha"])
    boundary = farm.get("boundary", [])

    monthly = context["monthly"]
    years = np.asarray(monthly["year"], int)
    last_year = int(years.max()) if years.size else config.SIM_END
    sel = years == last_year
    et0_m = monthly["et0"][sel] if sel.any() else np.zeros(12)
    pr_m = monthly["pr"][sel] if sel.any() else np.zeros(12)

    from ..domain.water import effective_rain_monthly

    pe_m = np.array([effective_rain_monthly(v) for v in pr_m])
    if pe_m.size < 12:
        pe_m = np.resize(pe_m, 12)

    # Reference crop for the season window and the Kc curve. With "None" planted
    # the field has no current crop, so anchor the indicative design on the first
    # preferred crop, then on the region's first crop.
    current_ids = [c.get("crop_id") for c in farm.get("current_crops", [])]
    preferred = [cid for cid in (profile.get("must_include") or []) if cid in catalog.crops()]
    region_id = farm.get("region_id") or "us_ks"
    fallback_id = preferred[0] if preferred else catalog.region(region_id).crops[0]
    primary = next((cid for cid in current_ids if cid in catalog.crops()), fallback_id)
    crop = catalog.crop(primary)
    kc = crop.kc_mid
    season_mask = irrigation_mod.season_month_mask(crop.sow_doy(), crop.season_length_days)
    existing = irrigation.get("system")

    if irrigation.get("status") != "irrigated":
        plan = irrigation_mod.rainfed_plan(float(np.sum(pr_m)), area_ha)
        plan.update({"parcel": {"area_ha": area_ha, "boundary": boundary}, "provenance": context_service.provenance_for(context)})
        return plan

    design = irrigation_mod.design(
        area_ha=area_ha,
        boundary=boundary,
        slope_pct=float(context["soil"].get("slope_pct", 2.0)),
        hours_per_day=float(irrigation.get("hours_per_day") or 12),
        flow_available_l_s=float(irrigation.get("flow_l_s") or 0),
        annual_limit_m3=float(irrigation.get("annual_limit_m3") or 0),
        et0_monthly=et0_m,
        pr_monthly=pr_m,
        pe_monthly=pe_m,
        kc=kc,
        head_m=40.0 + float(context["arrays"].get("cell", {}).get("elevation_m") or 0) * 0.01,
        season_mask=season_mask,
        existing_system=existing if existing in {s["id"] for s in irrigation_mod.SYSTEMS} else None,
    )
    design.update({"parcel": {"area_ha": area_ha, "boundary": boundary}, "provenance": context_service.provenance_for(context)})
    return design


# --------------------------------------------------------------------------
# F5
# --------------------------------------------------------------------------

_HAZARD_STATUS_ES = {
    "insufficient data": "sin datos suficientes",
    "observed": "observado",
    "high": "alto",
    "moderate": "moderado",
    "low": "bajo",
    "within tolerance": "dentro de tolerancia",
    "above tolerance": "por encima de la tolerancia",
    "near normal": "cerca de lo normal",
    "moderate drought": "sequía moderada",
    "severe drought": "sequía severa",
    "extreme drought": "sequía extrema",
}

_HAZARD_SOURCE_ES = {
    "hail": "Sin dataset en el catálogo del proyecto",
    "wildfire": "Sin producto FIRMS en el catálogo del proyecto",
}


def hazards_report(context: dict, locale: str = "en-US") -> dict:
    assessment = hazards_mod.assess(catalog.hazards(), context["hazard_inputs"])
    es_locale = locale.startswith("es")
    for entry in assessment:
        es = catalog.hazard_localised(entry["hazard"], "es-ES")
        entry["name_es"] = es["name"]
        entry["playbook_es"] = es["playbook"]
        status = entry.get("status")
        entry["status_es"] = _HAZARD_STATUS_ES.get(status, status) if status else status
        entry["source_es"] = _HAZARD_SOURCE_ES.get(entry["hazard"])
        if es_locale:
            entry["name"] = es["name"]
            entry["playbook"] = es["playbook"]
            if entry["status_es"]:
                entry["status"] = entry["status_es"]
            if entry["source_es"]:
                entry["source"] = entry["source_es"]
    pr = context["arrays"]["pr"]
    year = context["arrays"]["year"]
    month = context["arrays"]["month"]
    last = year == year.max()
    workability = hazards_mod.workability_windows(pr[last], year[last], month[last])
    return {
        "hazards": assessment,
        "current": {
            "spei3": context["drought"]["spei3"],
            "spei3_class": context["drought"]["spei3_class"],
            "add_days": context["drought"]["add_days"],
            "sm_rz_pct": context["drought"]["sm_rz_pct"],
        },
        "workability": workability,
    }
