"""Irrigation design (spec 10.11).

Indicative design: system choice, design flow, zones, monthly schedule and a
material list. No prices (D9) and no construction project (D10).
"""

from __future__ import annotations

import math

import numpy as np

from .water import design_flow_l_s, pump_power_kw

# efficiency, and 0-2 ratings where 0 is best (spec 10.11.3)
SYSTEMS: list[dict] = [
    {"id": "center_pivot", "name": "Center pivot", "name_es": "Pivote central", "eta": 0.82, "capex": 1, "slope": 0, "wind": 1, "sandy": 1, "labor": 0, "energy": 1},
    {"id": "pivot_lepa", "name": "Center pivot (LEPA)", "name_es": "Pivote central (LEPA)", "eta": 0.92, "capex": 2, "slope": 0, "wind": 1, "sandy": 1, "labor": 0, "energy": 1},
    {"id": "sdi", "name": "Subsurface drip (SDI)", "name_es": "Goteo subterráneo (SDI)", "eta": 0.90, "capex": 2, "slope": 0, "wind": 0, "sandy": 0, "labor": 0, "energy": 0},
    {"id": "furrow", "name": "Furrow", "name_es": "Surcos", "eta": 0.60, "capex": 0, "slope": 2, "wind": 0, "sandy": 1, "labor": 2, "energy": 0},
    {"id": "micro", "name": "Micro-irrigation", "name_es": "Microaspersión", "eta": 0.88, "capex": 2, "slope": 0, "wind": 0, "sandy": 0, "labor": 1, "energy": 0},
]

WEIGHTS = {"efficiency": 25, "capex": 20, "slope": 15, "wind": 15, "sandy": 10, "labor": 10, "energy": 5}


def score_system(system: dict, slope_pct: float, existing_system: str | None = None) -> float:
    slope_penalty = 0.0
    if slope_pct > 8:
        slope_penalty = 1.0 if system["slope"] >= 2 else 0.5
    elif slope_pct > 3:
        slope_penalty = 0.5 if system["slope"] >= 2 else 0.0
    else:
        slope_penalty = 0.0

    penalty = (
        WEIGHTS["efficiency"] * (1.0 - system["eta"])
        + WEIGHTS["capex"] * system["capex"] / 2.0
        + WEIGHTS["slope"] * slope_penalty
        + WEIGHTS["wind"] * system["wind"] / 2.0
        + WEIGHTS["sandy"] * system["sandy"] / 2.0
        + WEIGHTS["labor"] * system["labor"] / 2.0
        + WEIGHTS["energy"] * system["energy"] / 2.0
    )
    score = max(0.0, 100.0 - penalty)
    # equipment already on the farm is paid for: give it a realistic advantage
    if existing_system and system["id"] == existing_system:
        score = min(100.0, score + 12.0)
    return score


def rank_systems(slope_pct: float, existing_system: str | None = None) -> list[dict]:
    ranked = [{**s, "score": round(score_system(s, slope_pct, existing_system), 1)} for s in SYSTEMS]
    return sorted(ranked, key=lambda s: s["score"], reverse=True)


def split_into_zones(boundary: list[list[float]], n_zones: int) -> list[dict]:
    """Split the parcel bounding box into n_zones vertical strips (indicative)."""
    if not boundary:
        return []
    xs = [p[0] for p in boundary]
    ys = [p[1] for p in boundary]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    n = max(1, int(n_zones))
    step = (x1 - x0) / n
    zones = []
    for i in range(n):
        zones.append(
            {
                "id": f"Z{i + 1}",
                "boundary": [
                    [x0 + i * step, y0],
                    [x0 + (i + 1) * step, y0],
                    [x0 + (i + 1) * step, y1],
                    [x0 + i * step, y1],
                ],
                "system": None,
            }
        )
    return zones


def season_month_mask(sow_doy: int, length: int) -> np.ndarray:
    """Which calendar months the crop actually occupies (12 booleans)."""
    import datetime as dt

    mask = np.zeros(12, bool)
    for d in range(int(sow_doy), int(sow_doy) + int(length)):
        day = d if d <= 366 else d - 366
        month = (dt.date(2021, 1, 1) + dt.timedelta(days=day - 1)).month
        mask[month - 1] = True
    return mask


def monthly_schedule(
    et0_monthly: np.ndarray,
    pr_monthly: np.ndarray,
    kc: float,
    pe_monthly: np.ndarray,
    season_mask: np.ndarray | None = None,
) -> dict:
    etc = kc * np.asarray(et0_monthly, float)
    if season_mask is not None:
        etc = etc * np.asarray(season_mask, float)
    nir = np.maximum(0.0, etc - np.asarray(pe_monthly, float) * (0 if season_mask is None else np.asarray(season_mask, float)))
    return {
        "etc_mm": [round(float(v), 1) for v in etc],
        "pe_mm": [round(float(v), 1) for v in pe_monthly],
        "nir_mm": [round(float(v), 1) for v in nir],
        "seasonal_nir_mm": round(float(np.sum(nir)), 1),
        "peak_nir_mm": round(float(np.max(nir)), 1),
        "peak_month": int(np.argmax(nir) + 1),
    }


def materials_for(system_id: str, area_ha: float, zones: int, flow_l_s: float, head_m: float) -> list[dict]:
    """Bill of materials that actually matches the recommended system."""
    pump_kw = round(pump_power_kw(flow_l_s, head_m), 1)
    if system_id in ("center_pivot", "pivot_lepa"):
        import math as _math

        radius_m = _math.sqrt(area_ha * 10000 / _math.pi)
        spans = max(1, int(_math.ceil(radius_m / 55.0)))
        return [
            {"item": "Pivot spans (55 m)", "item_es": "Tramos de pivote (55 m)", "quantity": spans},
            {"item": "Sprinkler packages", "item_es": "Paquetes de aspersores", "quantity": spans * 8},
            {"item": "Pivot point + pad", "item_es": "Punto de pivote + base", "quantity": 1},
            {"item": "Pump (kW)", "item_es": "Bomba (kW)", "quantity": pump_kw},
            {"item": "Controller", "item_es": "Programador", "quantity": 1},
        ]
    if system_id == "furrow":
        return [
            {"item": "Furrow ditching (m)", "item_es": "Acequias (m)", "quantity": int(area_ha * 10000 / 1.5)},
            {"item": "Gated pipe (m)", "item_es": "Tubería con compuertas (m)", "quantity": int(area_ha * 10000 / 20)},
            {"item": "Pump (kW)", "item_es": "Bomba (kW)", "quantity": pump_kw},
        ]
    # drip / micro
    laterals_m = int(area_ha * 10000 / 2.0)
    return [
        {"item": "Lateral pipe (m)", "item_es": "Tubería lateral (m)", "quantity": laterals_m},
        {"item": "Emitters", "item_es": "Emisores", "quantity": int(laterals_m / 0.5)},
        {"item": "Zone valves", "item_es": "Válvulas de zona", "quantity": zones},
        {"item": "Filter unit", "item_es": "Unidad de filtrado", "quantity": 1},
        {"item": "Pump (kW)", "item_es": "Bomba (kW)", "quantity": pump_kw},
        {"item": "Controller", "item_es": "Programador", "quantity": 1},
    ]


def design(
    area_ha: float,
    boundary: list[list[float]],
    slope_pct: float,
    hours_per_day: float,
    flow_available_l_s: float,
    annual_limit_m3: float,
    et0_monthly: np.ndarray,
    pr_monthly: np.ndarray,
    pe_monthly: np.ndarray,
    kc: float,
    head_m: float = 40.0,
    season_mask: np.ndarray | None = None,
    existing_system: str | None = None,
) -> dict:
    """Return the indicative irrigation design."""
    schedule = monthly_schedule(et0_monthly, pr_monthly, kc, pe_monthly, season_mask)
    ranked = rank_systems(slope_pct, existing_system)
    top = ranked[0]

    peak_nir_mm = max(schedule["peak_nir_mm"], 1.0)
    daily_peak_mm = peak_nir_mm / 30.0
    q_required = design_flow_l_s(daily_peak_mm, area_ha, top["eta"], max(hours_per_day, 1.0))

    supply = flow_available_l_s if flow_available_l_s > 0 else q_required
    zones_needed = max(1, int(math.ceil(q_required / max(supply, 1e-6))))
    zones = split_into_zones(boundary, zones_needed)
    for z in zones:
        z["system"] = top["id"]
        z["area_ha"] = round(area_ha / zones_needed, 2)

    seasonal_nir = schedule["seasonal_nir_mm"]
    volume_m3 = seasonal_nir * area_ha * 10.0 / top["eta"]
    within_right = True
    if annual_limit_m3 and annual_limit_m3 > 0:
        within_right = volume_m3 <= annual_limit_m3

    materials = materials_for(top["id"], area_ha, zones_needed, q_required, head_m)

    return {
        "system": {"id": top["id"], "name": top["name"], "name_es": top.get("name_es"), "efficiency": top["eta"], "score": top["score"]},
        "alternatives": ranked[1:],
        "design_flow_l_s": round(q_required, 2),
        "supply_flow_l_s": round(supply, 2),
        "zones": zones,
        "schedule": schedule,
        "volume_m3": round(volume_m3, 0),
        "annual_limit_m3": annual_limit_m3,
        "within_water_right": within_right,
        "materials": materials,
        "caveats": [
            "Indicative design. A technical project is required for construction.",
            "Application rate must be checked against the soil infiltration rate on site.",
        ],
        "caveats_es": [
            "Diseño orientativo. Para ejecutar la obra se requiere un proyecto técnico.",
            "La tasa de aplicación debe comprobarse contra la velocidad de infiltración del suelo en campo.",
        ],
    }


def rainfed_plan(annual_pr_mm: float, area_ha: float) -> dict:
    """What to do when there is no water right: no irrigation, only practices."""
    capture_area = area_ha * 0.15
    volume = capture_area * 10000 * (annual_pr_mm * 0.7) * 0.5 * 0.85 / 1000.0
    return {
        "system": {"id": "rainfed", "name": "Rainfed", "name_es": "Secano", "efficiency": None, "score": None},
        "capture": {
            "catchment_ha": round(capture_area, 2),
            "potential_volume_m3": round(volume, 0),
            "runoff_coefficient": 0.5,
        },
        "practices": [
            "Keep residue on the surface to store rainfall",
            "Rotate to lower-water-demand crops",
            "Use a cover crop to improve infiltration",
            "Avoid tillage that destroys soil structure",
        ],
        "practices_es": [
            "Mantener rastrojo en superficie para almacenar lluvia",
            "Rotar a cultivos de menor demanda de agua",
            "Usar una cubierta para mejorar la infiltración",
            "Evitar labores que destruyan la estructura del suelo",
        ],
        "caveats": ["No irrigation water declared: this is a dryland plan, not an irrigation design."],
        "caveats_es": ["No hay agua de riego declarada: es un plan de secano, no un diseño de riego."],
    }
