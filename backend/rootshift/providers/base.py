"""Shared provider plumbing: HTTP with retries, disk cache, provenance."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .. import catalog, config

USER_AGENT = "ROOTSHIFT/2.0 (hackathon demo; contact: team)"


def _assert_online() -> None:
    """Demo mode must be able to run with the network unplugged.

    Set ROOTSHIFT_OFFLINE=1 to prove it: any provider call then fails loudly
    instead of hanging on a socket.
    """
    if os.getenv("ROOTSHIFT_OFFLINE", "").strip().lower() in ("1", "true", "yes"):
        raise RuntimeError("offline mode: provider network access is blocked")


def _cache_path(prefix: str, key: str) -> Path:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return config.CACHE_DIR / f"{prefix}_{digest}.json"


def read_cache(prefix: str, key: str) -> dict | None:
    path = _cache_path(prefix, key)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None
    return None


def write_cache(prefix: str, key: str, payload: dict) -> None:
    config.ensure_dirs()
    path = _cache_path(prefix, key)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, default=_json_default)


def _json_default(obj):
    """numpy -> JSON."""
    import numpy as np

    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def http_json(url: str, payload: dict | None = None, timeout: int = 60, retries: int = 3) -> dict:
    _assert_online()
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"User-Agent": USER_AGENT}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception as exc:  # network hiccup
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"request failed after {retries} attempts: {last_error}")


def http_text(url: str, payload: dict | None = None, timeout: int = 60, retries: int = 3) -> str:
    _assert_online()
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"User-Agent": USER_AGENT}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2 ** attempt)
    raise RuntimeError("text request failed")


def provenance(product_id: str, variable: str, unit: str, period: str, resolution: str, **extra) -> dict:
    meta = catalog.product(product_id)
    payload = {
        "product_id": meta["id"],
        "product": meta["name"],
        "short_name": meta.get("short_name"),
        "variable": variable,
        "unit": unit,
        "resolution": resolution,
        "period": period,
        "model_version": config.MODEL_VERSION,
    }
    payload.update(extra)
    return payload
