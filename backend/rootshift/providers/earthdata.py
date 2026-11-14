"""Earthdata Login access (spec 7.2): token, CMR and OPeNDAP subsetting.

The token is read from the environment or from `backend/.env` (gitignored). It is
never logged and never written into a response.

OPeNDAP is used instead of downloading granules: a 19 MB monthly IMERG file can
be downloaded at ~0.5 MB/s (35 s), while an OPeNDAP subset for the Kansas window
returns in ~0.8 s. For a 24-year series that is the difference between 3 hours and
2 minutes.
"""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .. import config

USER_AGENT = "ROOTSHIFT/2.0 (hackathon; contact: team)"


class EarthdataError(RuntimeError):
    pass


def _read_dotenv() -> dict[str, str]:
    path = config.BACKEND_DIR / ".env"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def token() -> str | None:
    value = os.getenv("EARTHDATA_TOKEN")
    if value:
        return value.strip()
    return _read_dotenv().get("EARTHDATA_TOKEN")


def has_token() -> bool:
    return bool(token())


def headers() -> dict[str, str]:
    tok = token()
    if not tok:
        raise EarthdataError("EARTHDATA_TOKEN is not configured")
    return {"Authorization": f"Bearer {tok}", "User-Agent": USER_AGENT}


def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers=headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read()[:200].decode("utf-8", "replace")
        raise EarthdataError(f"HTTP {exc.code} for {url.split('?')[0]}: {body}") from exc


# --------------------------------------------------------------------------
# CMR
# --------------------------------------------------------------------------

CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.json"


def cmr_granules(short_name: str, temporal: str | None = None, page_size: int = 3, version: str | None = None) -> list[dict]:
    params = {"short_name": short_name, "page_size": page_size, "sort_key": "-start_date"}
    if temporal:
        params["temporal"] = temporal
    if version:
        params["version"] = version
    url = CMR_GRANULES + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return __import__("json").loads(resp.read())["feed"]["entry"]


def granule_data_url(entry: dict) -> str:
    for link in entry.get("links", []):
        if link.get("rel", "").endswith("data#"):
            return link["href"]
    raise EarthdataError("granule has no data link")


# --------------------------------------------------------------------------
# OPeNDAP
# --------------------------------------------------------------------------

_ROW = re.compile(r"^\s*([A-Za-z0-9_]+)\[(\d+)\](?:\[(\d+)\])?,(.*)$")


def parse_ascii(payload: str) -> dict[str, list[list[float]]]:
    """Parse an OPeNDAP .ascii response into {variable: [[values per row]]}.

    Rows look like `precipitation[0][3], 0.2, 0.3, ...`: the first bracket is the
    outer index (time), the second is the first spatial index.
    """
    out: dict[str, list[list[float]]] = {}
    for line in payload.splitlines():
        match = _ROW.match(line)
        if not match:
            continue
        name = match.group(1)
        values = []
        for cell in match.group(4).split(","):
            cell = cell.strip()
            if not cell:
                continue
            try:
                values.append(float(cell))
            except ValueError:
                values.append(float("nan"))
        out.setdefault(name, []).append(values)
    return out


def opendap_ascii(url: str, constraint: str) -> dict[str, list[list[float]]]:
    """Fetch one variable slice from an OPeNDAP dataset URL."""
    payload = _get(f"{url}.ascii?{constraint}").decode("utf-8", "replace")
    parsed = parse_ascii(payload)
    if not parsed:
        raise EarthdataError(f"empty OPeNDAP response for {constraint}")
    return parsed
