"""The demo must run with the network unplugged (spec D18).

These tests prove that building the full context from a fixture performs zero
network I/O, and that the provider layer fails loudly when forced offline.
"""

from __future__ import annotations

import json

import pytest

from rootshift import config
from rootshift.providers import base as provider_base
from rootshift.services import context as context_service
from rootshift.services import farm_service


def _fixture(demo_id: str) -> dict:
    return json.loads((config.FIXTURES_DIR / f"{demo_id}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("demo_id", ["demo_finney", "demo_greeley", "demo_republic"])
def test_context_build_makes_no_network_calls(monkeypatch, demo_id):
    calls = []

    def boom(*args, **kwargs):
        calls.append(args)
        raise AssertionError("network call attempted while building the demo context")

    monkeypatch.setattr(provider_base, "http_json", boom)
    monkeypatch.setattr(provider_base, "http_text", boom)

    context_service.CACHE.clear()
    ctx = context_service.build_context(_fixture(demo_id), {"objective": "balanced"})
    assert ctx["crop_matrix"]["corn"]["years"]
    assert ctx["confidence"] > 0
    assert calls == []


def test_full_rotation_makes_no_network_calls(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network call attempted while computing F1")

    monkeypatch.setattr(provider_base, "http_json", boom)
    monkeypatch.setattr(provider_base, "http_text", boom)

    context_service.CACHE.clear()
    ctx = context_service.build_context(_fixture("demo_republic"), {"objective": "balanced"})
    result = farm_service.build_rotation(
        ctx,
        {
            "objective": "balanced",
            "risk_tolerance": "medium",
            "horizon_seasons": 8,
            "max_crops": 4,
            "must_include": [],
            "excluded_crops": [],
        },
    )
    assert len(result["sequence"]) == 8
    assert 0 <= result["irs"]["value"] <= 100


def test_provider_layer_refuses_when_offline(monkeypatch):
    monkeypatch.setenv("ROOTSHIFT_OFFLINE", "1")
    with pytest.raises(RuntimeError, match="offline"):
        provider_base.http_json("https://example.invalid")
    with pytest.raises(RuntimeError, match="offline"):
        provider_base.http_text("https://example.invalid")
