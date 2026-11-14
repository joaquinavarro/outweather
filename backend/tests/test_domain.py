"""Golden tests for the calculation engine (spec 16.2).

These lock the formulas: changing a formula must break a test.
"""

from __future__ import annotations

import numpy as np
import pytest

from rootshift.domain import climate, disease, drought, erosion, nutrients, resilience, rotation, scenarios, water
from rootshift.domain import yield_model as ym


# T1 --- ET0 ---------------------------------------------------------------

def test_et0_summer_day_is_physically_plausible():
    """A clear Kansas summer day must give 5-10 mm/day, and more radiation -> more ET0."""
    args = dict(lat_deg=38.05, doy=np.array([200]), elev_m=858.0)
    low = climate.eto_fao56(
        np.array([30.0]), np.array([17.0]), np.array([13.0]),
        np.array([18.0]), np.array([2.0]), np.array([92.0]), **args
    )[0]
    high = climate.eto_fao56(
        np.array([34.0]), np.array([20.0]), np.array([14.0]),
        np.array([28.0]), np.array([4.0]), np.array([92.0]), **args
    )[0]
    assert 4.0 <= low <= 11.0
    assert high > low
    assert high <= 13.0


def test_et0_is_zero_at_night_radiation():
    et0 = climate.eto_fao56(
        np.array([10.0]), np.array([2.0]), np.array([0.0]),
        np.array([0.0]), np.array([0.0]), np.array([95.0]),
        lat_deg=38.05, doy=np.array([15]), elev_m=800.0,
    )[0]
    assert et0 >= 0.0
    assert et0 < 0.5


# T2/T3 --- water balance ---------------------------------------------------

def test_water_balance_stores_rain_when_no_et():
    taw = 170.0
    bal = water.water_balance(
        pr_mm=np.array([100.0, 0.0]), et0_mm=np.array([0.0, 0.0]),
        kc=np.array([0.0, 0.0]), taw=taw, p_depletion=0.5, d0=0.5 * taw,
    )
    assert bal["d"][0] == pytest.approx(max(0.0, 0.5 * taw - 100.0), abs=1e-6)


def test_ks_bounds():
    assert water.ks_factor(10.0, taw=170.0, raw=85.0) == 1.0
    assert water.ks_factor(170.0, taw=170.0, raw=85.0) == 0.0
    mid = water.ks_factor(127.5, taw=170.0, raw=85.0)
    assert 0.0 < mid < 1.0


def test_effective_rain_is_below_gross_rain():
    for p in (10, 60, 120, 300):
        assert 0 <= water.effective_rain_monthly(p) <= p + 1e-9


def test_taW_matches_definition():
    assert water.taw_mm(0.30, 0.15, 1.0) == pytest.approx(150.0)


# T4 --- drought indices ----------------------------------------------------

def test_spei_detects_injected_drought():
    rng = np.random.default_rng(1)
    months = 30 * 12
    pr = rng.normal(50, 10, months).clip(1)
    pet = np.full(months, 40.0)
    # inject 6 very dry months
    pr[-6:] = 2.0
    z = drought.spei(pr, pet, 3)
    assert np.nanmin(z) < -1.5
    assert drought.classify(np.nanmin(z)) in ("severe drought", "extreme drought")


def test_classify_ranges():
    assert drought.classify(2.5) == "extremely wet"
    assert drought.classify(0.0) == "near normal"
    assert drought.classify(-2.2) == "extreme drought"


# T5 --- yield model --------------------------------------------------------

def test_yield_ratio_is_one_without_water_stress():
    assert ym.water_limited_ratio(1.25, 1.0) == pytest.approx(1.0)


def test_yield_ratio_at_zero_et():
    assert ym.water_limited_ratio(1.25, 0.0) == pytest.approx(0.0)


def test_heat_and_frost_factors_are_monotone():
    assert ym.heat_factor(0, 60) == 1.0
    assert ym.heat_factor(60, 60) < ym.heat_factor(30, 60)
    assert ym.frost_factor(0, 20) == 1.0
    assert ym.frost_factor(20, 20) < ym.frost_factor(10, 20)


def test_rotation_multiplier_rules():
    cfg = {
        "default": 1.0,
        "pairs": [{"from": "alfalfa", "to": "*", "value": 1.12}],
        "rules": [
            {"from_family": "fabaceae", "to_family": "poaceae", "value": 1.10},
            {"from_same_as_to": True, "value": 0.80},
            {"from_family_equals_to_family": True, "value": 0.75},
        ],
    }
    corn = {"id": "corn", "family": "poaceae"}
    soy = {"id": "soybean", "family": "fabaceae"}
    alfalfa = {"id": "alfalfa", "family": "fabaceae"}
    assert ym.rotation_multiplier(cfg, None, corn) == 1.0
    assert ym.rotation_multiplier(cfg, alfalfa, corn) == 1.12
    assert ym.rotation_multiplier(cfg, soy, corn) == 1.10
    assert ym.rotation_multiplier(cfg, corn, corn) == 0.80
    assert ym.rotation_multiplier(cfg, {"id": "oats", "family": "poaceae"}, corn) == 0.75


# T6 --- ADD -----------------------------------------------------------------

def test_add_counts_days_below_percentile():
    years = np.repeat(np.arange(2015, 2025), 365)
    doy = np.tile(np.arange(1, 366), 10)
    rng = np.random.default_rng(3)
    sm = rng.normal(0.25, 0.02, years.size)
    # make the last year clearly dry
    sm[-365:] = 0.05
    mask = years == 2024
    count, pct = drought.agricultural_drought_days(sm, years, doy, mask, threshold=20)
    assert count > 300


# T7 --- erosion -------------------------------------------------------------

def test_r_factor_is_zero_without_rain():
    assert np.all(erosion.r_factor_monthly(np.zeros(365), np.tile(np.arange(1, 13), 31)[:365]) == 0)


def test_rusle_scales_linearly():
    a1 = erosion.rusle(1000, 0.4, 0.3, 0.2)
    a2 = erosion.rusle(2000, 0.4, 0.3, 0.2)
    assert a2 == pytest.approx(2 * a1)


# T8 --- return period -------------------------------------------------------

def test_return_period_grows_with_value():
    series = np.array([10, 12, 9, 14, 11, 13, 15, 8, 12, 16, 10, 11], float)
    t_low = drought.return_period(series, 10.0)
    t_high = drought.return_period(series, 18.0)
    assert t_high > t_low


# T9/T10 --- resilience ------------------------------------------------------

def test_irs_is_bounded():
    cfg = {"irs": {"weights": {"water": 0.25, "stability": 0.2, "soil": 0.2, "diversity": 0.15, "health": 0.1, "hazard": 0.1},
                   "water": {"et_ratio_weight": 0.5, "coverage_weight": 0.3, "groundwater_weight": 0.2,
                             "groundwater_penalty_declining": 0.5, "groundwater_penalty_critical": 0.0,
                             "groundwater_critical_mm_year": -10},
                   "stability": {"cv_ceiling": 0.5},
                   "soil": {"nee_weight": 0.25, "npp_weight": 0.2, "erosion_weight": 0.25, "legume_weight": 0.15,
                            "nitrogen_weight": 0.15, "npp_reference_gc_m2_year": 600, "erosion_tolerance_t_ha_year": 7,
                            "nee_neutral_band": 20, "nitrogen_deficit_soft_kg_ha": 20}}}
    comp = {"water": 80, "stability": 60, "soil": 70, "diversity": 50, "health": 90, "hazard": 40}
    result = resilience.composite(comp, cfg["irs"]["weights"])
    assert 0 <= result["value"] <= 100
    assert abs(sum(result["contributions"].values()) - result["value"]) < 0.5


def test_shannon_is_max_with_equal_families():
    value, h = resilience.shannon_diversity(["poaceae", "fabaceae", "asteraceae", "brassicaceae"], max_crops=4)
    assert 95 <= value <= 100
    assert h == pytest.approx(np.log(4), abs=1e-9)


# T11 --- nutrients ----------------------------------------------------------

def test_nutrient_removal_follows_coefficients():
    coefficients = {"corn": {"n_removal_kg_per_t": 15.5, "p2o5_removal_kg_per_t": 6.4, "k2o_removal_kg_per_t": 4.4, "n_fixation_kg_per_ha": 0.0}}
    seq = [{"crop_id": "corn"}]
    rem = nutrients.rotation_nutrients(seq, [10.0], [1.0], coefficients)
    assert rem["n_removal_kg_ha"] == pytest.approx(155.0, abs=0.1)
    bal = nutrients.balance(rem, {"n_kg_ha": 100})
    assert bal["n_balance_kg_ha"] == pytest.approx(-55.0, abs=0.1)


# T12 --- scenarios ----------------------------------------------------------

def test_gaez_multiplier_applied_once():
    gaez = {"corn": {"rcp45": {"yield_multiplier": 0.95, "water_multiplier": 1.15}}}
    y, w = scenarios.scenario_adjustment({"id": "corn"}, "S6", gaez)
    assert y == pytest.approx(0.95)
    assert w == pytest.approx(1.15)
    y0, w0 = scenarios.scenario_adjustment({"id": "corn"}, "S0", gaez)
    assert (y0, w0) == (1.0, 1.0)


def test_rotation_constraints_reject_same_species_back_to_back():
    cons = rotation.Constraints(n_seasons=4, max_crops=4)
    meta = {
        "corn": {"id": "corn", "family": "poaceae", "stand_seasons": 1},
        "soybean": {"id": "soybean", "family": "fabaceae", "stand_seasons": 1},
    }
    # the classic corn-soybean rotation must be allowed
    assert rotation._sequence_valid(["corn", "soybean", "corn", "soybean"], meta, cons)
    # same species back to back must never be allowed
    assert not rotation._sequence_valid(["corn", "corn"], meta, cons)


def test_disease_index_is_bounded_and_monotone():
    dry = np.zeros(100)
    wet = np.full(100, 0.8)
    assert disease.disease_index(dry) == 0.0
    assert 0 <= disease.disease_index(wet) <= 100
    assert disease.disease_index(wet) > disease.disease_index(dry)


def test_lwd_proxy_bounds():
    lwd = disease.lwd_proxy(
        rh=np.array([95.0, 40.0]), tmin=np.array([12.0, 20.0]),
        tdew=np.array([12.0, 5.0]), pr=np.array([0.0, 5.0]),
    )
    assert np.all(lwd >= 0) and np.all(lwd <= 24)
    assert lwd[0] > lwd[1]


# T13 --- hazards ------------------------------------------------------------

def test_hazard_return_periods_are_capped_and_consistent():
    from rootshift import catalog
    from rootshift.domain import hazards

    years = list(range(2001, 2025))
    data = {
        "spei12_by_year": {y: -2.5 if i % 2 else 0.3 for i, y in enumerate(years)},
        "rx1day_by_year": {y: 40 + (i % 5) * 8 for i, y in enumerate(years)},
        "frost_years": {y: i % 4 == 0 for i, y in enumerate(years)},
        "heat_years": {y: True for y in years},
        "wind_years": {y: i % 3 == 0 for i, y in enumerate(years)},
        "runoff_pct": 0.6,
        "slope_pct": 2.0,
        "hydgrp": "B",
        "erosion_t_ha_year": 3.0,
        "erosion_tolerance": 7.0,
        "add_days": 10,
        "drought_class": "severe drought",
    }
    report = hazards.assess(catalog.hazards(), data)
    for entry in report:
        t = entry.get("return_period_years")
        if t is not None:
            assert t <= 50.0, (entry["hazard"], t)

    flood = next(e for e in report if e["hazard"] == "flood")
    if flood["p_annual"] and flood["return_period_years"]:
        assert flood["return_period_years"] == pytest.approx(1.0 / flood["p_annual"], rel=0.15)

    heat = next(e for e in report if e["hazard"] == "heat")
    assert heat["p_annual"] == pytest.approx(1.0)
    assert heat["return_period_years"] == 1.0


def test_hazards_without_data_have_no_probability():
    from rootshift import catalog
    from rootshift.domain import hazards

    report = hazards.assess(catalog.hazards(), {})
    for entry in report:
        assert "p_annual" in entry
        assert "playbook" in entry
    hail = next(e for e in report if e["hazard"] == "hail")
    assert hail["calculable"] is False
    assert hail["p_annual"] is None
