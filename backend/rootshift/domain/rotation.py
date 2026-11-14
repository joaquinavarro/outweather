"""Rotation engine (spec 10.7).

Beam search over crop sequences (additive surrogate) + full Monte Carlo
evaluation of the best candidates + local search. No MILP (D4 = C).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

from . import scenarios as scen
from .yield_model import rotation_multiplier


@dataclass
class Constraints:
    n_seasons: int = 8
    # A one-season gap allows the standard corn-soybean rotation; with a gap of
    # two, corn-soy-corn would be rejected, which is agronomically wrong in the
    # US Corn Belt and in Kansas. Configurable per request.
    family_gap: int = 1
    max_crops: int = 4
    # The crop the farmer already has, pinned to season one (None = no current
    # crop, i.e. the "None" choice in the design panel).
    first_crop: str | None = None
    must_include: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    leggap: int = 3


def _allowed(
    state_ids: list[str],
    state_families: list[str],
    meta: dict[str, dict],
    crop_id: str,
    cons: Constraints,
) -> bool:
    fam = meta[crop_id]["family"]
    # R3: same species never in consecutive seasons
    if state_ids and state_ids[-1] == crop_id:
        return False
    # R2: same family separated by at least `family_gap` seasons
    recent = state_families[-cons.family_gap :]
    if fam in recent:
        return False
    # R8: max distinct species
    if crop_id not in state_ids and len(set(state_ids)) >= cons.max_crops:
        return False
    # R11: a perennial stand occupies several seasons and needs a break after it.
    stand = int(meta[crop_id].get("stand_seasons", 1))
    if stand > 1 and crop_id in state_ids[-stand:]:
        return False
    return True


def _diversity_penalty(state_ids: list[str]) -> float:
    if not state_ids:
        return 0.0
    return 0.0


def beam_search(
    candidates: list[dict],
    context: dict,
    cons: Constraints,
    beam_width: int = 48,
    water_limit_mm: float | None = None,
) -> list[tuple[list[str], float]]:
    """Return up to `beam_width` sequences ranked by the additive surrogate."""
    families = {c["id"]: c for c in candidates}
    by_id = {c["id"]: c for c in candidates}
    matrix = context["crop_matrix"]
    effects = context["rotation_effects"]

    mean_yield = {}
    nir_p80 = {}
    for c in candidates:
        m = matrix.get(c["id"])
        if not m:
            continue
        mean_yield[c["id"]] = float(np.mean(m["yield_rel"])) * float(m["ym_t_ha"])
        nir_p80[c["id"]] = float(np.percentile(m["nir_mm"], 80)) if m["nir_mm"] else 0.0

    usable = [
        c
        for c in candidates
        if c["id"] in mean_yield
        and (water_limit_mm is None or nir_p80[c["id"]] <= 0.95 * water_limit_mm)
    ]
    if not usable:
        usable = [c for c in candidates if c["id"] in mean_yield]
    if not usable:
        return []

    # The current crop and every crop the farmer explicitly selected are always
    # eligible, even if water-stressed: the app models what they actually have
    # and want, and lets the lower yield speak for itself.
    first = cons.first_crop if (cons.first_crop and cons.first_crop in by_id and cons.first_crop in mean_yield) else None
    must = [m for m in cons.must_include if m in by_id and m in mean_yield]
    usable_ids = {c["id"] for c in usable}
    for required_id in ([first] if first else []) + must:
        if required_id not in usable_ids:
            usable.insert(0, by_id[required_id])
            usable_ids.add(required_id)

    # Beam over seasons. `first` pins season one; a lookahead reserves the last
    # seasons for any not-yet-placed required crop so `must` is guaranteed.
    states = [(list(), list(), 0.0, 0.0)]
    for k in range(cons.n_seasons):
        nxt = []
        remaining = cons.n_seasons - k
        for ids, fams, area_sum, score in states:
            unused = [m for m in must if m not in ids]
            if len(unused) > remaining:
                continue
            if k == 0 and first:
                allowed = [c for c in usable if c["id"] == first]
            elif len(unused) >= remaining:
                allowed = [c for c in usable if c["id"] in unused]
            else:
                allowed = usable
            for c in allowed:
                if not _allowed(ids, fams, families, c["id"], cons):
                    continue
                prev = by_id[ids[-1]] if ids else None
                mult = rotation_multiplier(effects, prev, c)
                gain = mean_yield[c["id"]] * mult
                nxt.append((ids + [c["id"]], fams + [c["family"]], area_sum, score + gain))
        if not nxt:
            break
        nxt.sort(key=lambda s: s[3], reverse=True)
        states = nxt[: beam_width]

    # hard guarantees, filtered again for safety; missing legumes stay a soft penalty
    scored = []
    for ids, fams, _, score in states:
        if first and (not ids or ids[0] != first):
            continue
        if must and not set(must).issubset(set(ids)):
            continue
        legume_ok = any(f == "fabaceae" for f in fams)
        if not legume_ok:
            score *= 0.95
        scored.append((ids, score))
    scored.sort(key=lambda s: s[1], reverse=True)
    return scored


def _production_matrix(
    sequence: list[str],
    context: dict,
    members: np.ndarray,
    scenario_id: str,
    area_ha: float,
) -> dict:
    """Production as a 0-1 relative index and as tonnes of harvested product.

    The index (relative yield) is comparable across crops; tonnes are not
    (a tonne of hay is not a tonne of grain), so the objective and the headline
    metrics use the index and tonnes are kept for the per-crop detail table.
    """
    matrix = context["crop_matrix"]
    effects = context["rotation_effects"]
    gaez = context.get("gaez", {})
    cfg = context["simulation"]
    n_members, n_seasons = members.shape
    index = np.zeros((n_members, n_seasons), float)
    ym_vec = np.ones(n_seasons, float)

    for k, crop_id in enumerate(sequence):
        m = matrix.get(crop_id)
        if not m:
            continue
        crop = context["crops_by_id"][crop_id]
        ym_vec[k] = float(m["ym_t_ha"])
        if crop.get("cover"):
            # a cover crop is not harvested: it occupies the season but produces nothing
            index[:, k] = 0.0
            continue
        years = np.asarray(m["years"], int)
        yy = np.asarray(m["yield_rel"], float)
        pos = np.clip(np.searchsorted(years, members[:, k]), 0, len(years) - 1)
        yrel = yy[pos]
        prev = context["crops_by_id"][sequence[k - 1]] if k > 0 else None
        mult = rotation_multiplier(effects, prev, crop)
        y_mult, _ = scen.scenario_adjustment(crop, scenario_id, gaez)
        index[:, k] = np.clip(yrel * mult * y_mult, 0.0, 1.5)

    sigma = float(cfg.get("unmodeled_sigma", 0.0))
    if sigma > 0:
        # Unmodelled losses (hail, pests, management). Common random numbers:
        # the same noise applies to every candidate rotation, so comparisons are fair.
        rng = np.random.default_rng(cfg["seed"] + sum(ord(c) for c in scenario_id))
        noise = rng.lognormal(mean=-0.5 * sigma * sigma, sigma=sigma, size=index.shape)
        index = np.clip(index * noise, 0.0, 1.5)

    tonnes = index * ym_vec[None, :] * area_ha
    return {"index": index, "tonnes": tonnes, "area_ha": area_ha}


def metrics_from_production(prod: dict, cfg: dict) -> dict:
    area = max(prod["area_ha"], 1e-9)
    idx = prod["index"]  # (members, seasons), 0-1
    member_total = idx.mean(axis=1) if idx.size else np.array([0.0])
    mean = float(np.mean(member_total))
    sd = float(np.std(member_total))

    fail_line = cfg["failure_ratio"]
    good_line = cfg["good_year_ratio"]
    recovery_line = cfg["recovery_ratio"]

    p_fail = float(np.mean(idx < fail_line)) if idx.size else 0.0
    years_above = float(np.mean(idx >= good_line)) if idx.size else 0.0
    cvar10 = float(np.mean(np.sort(member_total)[: max(1, int(0.1 * member_total.size))]))

    rec = []
    for row in idx:
        if row.size == 0:
            continue
        worst = int(np.argmin(row))
        after = row[worst + 1 :]
        hits = np.where(after >= recovery_line)[0]
        rec.append(float(hits[0] + 1) if hits.size else float(row.size))
    recovery = float(np.mean(rec)) if rec else 0.0

    bad = idx < good_line
    p3 = 0.0
    if idx.shape[1] >= 3:
        run = np.zeros(idx.shape[0], bool)
        for i in range(idx.shape[1] - 2):
            run |= bad[:, i] & bad[:, i + 1] & bad[:, i + 2]
        p3 = float(np.mean(run))

    return {
        "production_index": round(100.0 * mean, 1),
        "p10_index": round(100.0 * float(np.percentile(member_total, 10)), 1),
        "p50_index": round(100.0 * float(np.percentile(member_total, 50)), 1),
        "p90_index": round(100.0 * float(np.percentile(member_total, 90)), 1),
        "cv": round(sd / mean, 4) if mean > 0 else 0.0,
        "cvar10_index": round(100.0 * cvar10, 1),
        "p_fail": round(p_fail, 4),
        "years_above_pct": round(years_above, 4),
        "recovery_years": round(recovery, 2),
        "p_drought3": round(p3, 4),
        "yield_mean_t_ha": round(float(np.mean(prod["tonnes"])) / area, 3),
        "total_t_per_year": round(float(np.mean(prod["tonnes"].sum(axis=1))) / max(idx.shape[1], 1), 1),
    }


def evaluate_sequence(
    sequence: list[str],
    context: dict,
    area_ha: float,
    n_members: int,
    seed: int,
    only: list[str] | None = None,
) -> dict:
    cfg = context["simulation"]
    n_seasons = len(sequence)
    out = {}
    for s in scen.SCENARIO_DEFS:
        if only and s["id"] not in only:
            continue
        members = scen.build_members(context["pools"], s["id"], n_seasons, n_members, seed)
        prod = _production_matrix(sequence, context, members, s["id"], area_ha)
        out[s["id"]] = metrics_from_production(prod, cfg)
    return out


def objective(
    metrics: dict,
    sequence: list[str],
    context: dict,
    weights: dict,
    risk_mult: float,
    water_norm: float,
) -> float:
    """Weighted objective J (spec 10.7.6), normalised to 0-1 pieces."""
    crop_ids = context["crops_by_id"]
    families = [crop_ids[c]["family"] for c in sequence]
    counts: dict[str, int] = {}
    for f in families:
        counts[f] = counts.get(f, 0) + 1
    n = max(len(families), 1)
    shannon = 0.0
    for f in counts:
        p = counts[f] / n
        shannon -= p * np.log(p)
    diversity = shannon / np.log(max(4, 1))

    prod_norm = min(1.0, metrics["production_index"] / 100.0)
    stability = max(0.0, 1.0 - min(1.0, metrics["cv"] / 0.5)) * (1.0 - metrics["p_fail"])

    return float(
        weights["production"] * prod_norm
        + weights["resilience"] * stability
        + weights["water"] * water_norm
        + weights["diversity"] * min(1.0, diversity)
        - weights["failure"] * risk_mult * metrics["p_fail"]
        - weights["cv"] * min(1.0, metrics["cv"])
    )


def _local_search(
    best: list[str],
    candidates: list[dict],
    context: dict,
    cons: Constraints,
    area_ha: float,
    n_members: int,
    seed: int,
    score_fn,
    rounds: int = 2,
) -> tuple[list[str], float]:
    current = list(best)
    current_score = score_fn(current)
    ids = [c["id"] for c in candidates]
    meta = {c["id"]: c for c in candidates}
    for _ in range(rounds):
        improved = False
        for i in range(len(current)):
            for cand in ids:
                if cand == current[i]:
                    continue
                trial = current[:]
                trial[i] = cand
                if not _sequence_valid(trial, meta, cons):
                    continue
                sc = score_fn(trial)
                if sc > current_score + 1e-9:
                    current, current_score = trial, sc
                    improved = True
        if not improved:
            break
    return current, current_score


def _sequence_valid(seq: list[str], meta: dict[str, dict], cons: Constraints) -> bool:
    ids: list[str] = []
    fams: list[str] = []
    for cid in seq:
        if not _allowed(ids, fams, meta, cid, cons):
            return False
        ids.append(cid)
        fams.append(meta[cid]["family"])
    if cons.first_crop and seq[0] != cons.first_crop:
        return False
    if cons.must_include and not set(cons.must_include).issubset(set(seq)):
        return False
    return True


def optimize(
    candidates: list[dict],
    context: dict,
    cons: Constraints,
    area_ha: float,
    objective_name: str = "balanced",
    risk_tolerance: str = "medium",
    water_limit_mm: float | None = None,
    water_norm: float = 0.5,
) -> dict:
    """Full F1 pipeline: beam search -> MC evaluation -> local search."""
    scoring = context["scoring"]
    weights = scoring["objective_weights"].get(objective_name, scoring["objective_weights"]["balanced"])
    risk_mult = scoring["risk_tolerance_multiplier"].get(risk_tolerance, 1.0)
    sim = context["simulation"]

    ranked = beam_search(candidates, context, cons, beam_width=sim["beam_width"], water_limit_mm=water_limit_mm)
    if not ranked:
        return {"sequence": [], "metrics": {}, "scenarios": {}, "candidates": []}

    def score_fn(seq: list[str], n_members: int = 300) -> tuple[float, dict, dict]:
        sc = evaluate_sequence(seq, context, area_ha, n_members, sim["seed"], only=["S0"])
        m = sc["S0"]
        return objective(m, seq, context, weights, risk_mult, water_norm), m, sc

    scored = []
    for ids, _ in ranked[:20]:
        val, m, _sc = score_fn(ids)
        scored.append((val, ids, m))
    scored.sort(key=lambda t: t[0], reverse=True)

    best_val, best_ids, best_m = scored[0]
    search_ids, search_val = _local_search(
        best_ids,
        candidates,
        context,
        cons,
        area_ha,
        sim["seed"],
        sim["seed"],
        lambda s: score_fn(s)[0],
    )
    if search_val > best_val:
        best_ids = search_ids
        best_val = search_val

    final_scen = evaluate_sequence(best_ids, context, area_ha, sim["n_scenarios"], sim["seed"])
    final_metrics = final_scen["S0"]

    return {
        "sequence": best_ids,
        "metrics": final_metrics,
        "scenarios": final_scen,
        "objective_value": round(best_val, 4),
        "evaluated": len(ranked),
    }


def baseline_sequence(current_crops: list[dict], n_seasons: int) -> list[str]:
    """Expand the farm's current crop mix cyclically over the horizon."""
    ids = [c["crop_id"] for c in current_crops]
    if not ids:
        return []
    return [ids[k % len(ids)] for k in range(n_seasons)]


def sequence_items(sequence: list[str], context: dict, area_ha: float, start_year: int) -> list[dict]:
    seasons_per_year = context.get("seasons_per_year", 1)
    items = []
    for k, cid in enumerate(sequence):
        crop = context["crops_by_id"][cid]
        year = start_year + (k // max(seasons_per_year, 1))
        season = f"{year}" if seasons_per_year == 1 else f"{year}{'SW'[k % 2]}"
        matrix = context["crop_matrix"].get(cid, {})
        nir = float(np.mean(matrix["nir_mm"])) if matrix.get("nir_mm") else 0.0
        y = float(np.mean(matrix["yield_rel"])) * float(matrix.get("ym_t_ha", 0)) if matrix.get("yield_rel") else 0.0
        items.append(
            {
                "k": k + 1,
                "season": season,
                "crop_id": cid,
                "crop_name": crop["name_en"],
                "crop_name_es": crop.get("name_es", crop["name_en"]),
                "family": crop["family"],
                "area_ha": round(area_ha, 2),
                "stand_seasons": crop.get("stand_seasons", 1),
                "nir_mm": round(nir, 1),
                "yield_t_ha": round(y, 2),
                "is_legume": bool(crop.get("is_legume")),
            }
        )
    return items
