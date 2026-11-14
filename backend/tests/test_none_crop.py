"""Design-panel coherence: current crop pinned, preferred crops guaranteed, "None" works.

Guards the regression where an empty current-crop list ("None" in the design panel)
made the irrigation design index `current_crops[0]` and return a 500.
"""

from __future__ import annotations

import json

from rootshift import config
from rootshift.services import context as context_service
from rootshift.services import farm_service


def _fixture(demo_id: str, current_crops: list[dict], farm_id: str) -> dict:
    fixture = json.loads((config.FIXTURES_DIR / f"{demo_id}.json").read_text(encoding="utf-8"))
    fixture["farm"]["id"] = farm_id
    fixture["farm"]["current_crops"] = current_crops
    return fixture


def _profile(must_include: list[str]) -> dict:
    return {
        "objective": "balanced",
        "risk_tolerance": "medium",
        "horizon_seasons": 8,
        "max_crops": 4,
        "must_include": must_include,
        "excluded_crops": [],
    }


def test_current_crop_is_pinned_to_first_season():
    context_service.CACHE.clear()
    fixture = _fixture("demo_finney", [{"crop_id": "corn", "area_ha": 44.9, "season": "2025"}], "none_test_corn")
    profile = _profile(["soybean"])
    ctx = context_service.build_context(fixture, profile)

    result = farm_service.build_rotation(ctx, profile)
    ids = [item["crop_id"] for item in result["sequence"]]

    assert len(ids) == 8
    assert ids[0] == "corn", ids
    assert "soybean" in ids, ids

    # the disease panel covers the current crop plus the selected preferred crop
    diseases = farm_service.disease_report(ctx, None, profile=profile)
    assert {panel["crop_id"] for panel in diseases["crops"]} == {"corn", "soybean"}


def test_none_current_crop_uses_the_selection_and_does_not_crash():
    context_service.CACHE.clear()
    fixture = _fixture("demo_finney", [], "none_test_empty")
    profile = _profile(["soybean", "winter_wheat"])
    ctx = context_service.build_context(fixture, profile)

    result = farm_service.build_rotation(ctx, profile)
    ids = [item["crop_id"] for item in result["sequence"]]

    assert len(ids) == 8
    assert {"soybean", "winter_wheat"} <= set(ids), ids

    # the irrigation design must not crash with an empty current-crop list
    irrigation = farm_service.irrigation_report(ctx, profile=profile)
    assert irrigation["system"]["id"]

    # with no current crop the default disease set is every selected preferred crop
    diseases = farm_service.disease_report(ctx, None, profile=profile)
    assert {panel["crop_id"] for panel in diseases["crops"]} == {"soybean", "winter_wheat"}

    # an explicit crop list (e.g. the proposed rotation) is still honoured
    explicit = farm_service.disease_report(ctx, ids)
    assert explicit["crops"]
    assert {panel["crop_id"] for panel in explicit["crops"]} <= set(ids)
