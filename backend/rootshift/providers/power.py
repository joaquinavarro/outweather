"""NASA POWER daily provider (P15)."""

from __future__ import annotations

import datetime as dt

import numpy as np

from .base import http_json, read_cache, write_cache

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "T2MDEW",
    "RH2M",
    "WS2M",
    "ALLSKY_SFC_SW_DWN",
    "PS",
    "PRECTOTCORR",
]


def _parse(payload: dict) -> dict:
    props = payload.get("properties", {})
    params = props.get("parameter", {})
    dates = sorted(params.get("T2M", {}).keys())
    if not dates:
        raise ValueError("POWER response has no T2M series")

    def series(name):
        col = params.get(name, {})
        return np.array([float(col.get(d, np.nan)) for d in dates], float)

    out = {
        "dates": dates,
        "tmax": series("T2M_MAX"),
        "tmin": series("T2M_MIN"),
        "tmean": series("T2M"),
        "tdew": series("T2MDEW"),
        "rh": series("RH2M"),
        "ws": series("WS2M"),
        "rs": series("ALLSKY_SFC_SW_DWN"),
        "ps": series("PS"),
        "pr": series("PRECTOTCORR"),
    }
    for key in ("tmax", "tmin", "tmean", "tdew", "rh", "ws", "rs", "ps", "pr"):
        arr = out[key]
        arr[arr <= -900] = np.nan
        out[key] = arr

    geom = payload.get("geometry", {}).get("coordinates", [None, None, None])
    out["cell"] = {"lon": geom[0], "lat": geom[1], "elevation_m": geom[2]}
    out["header"] = payload.get("header", {})
    return out


def fetch_daily(lat: float, lon: float, start: str = "19910101", end: str = "20241231", use_cache: bool = True) -> dict:
    key = f"{lat:.4f}:{lon:.4f}:{start}:{end}"
    if use_cache:
        cached = read_cache("power", key)
        if cached:
            return cached

    payload = http_json(
        f"{POWER_URL}?parameters={','.join(PARAMS)}&community=AG&latitude={lat}&longitude={lon}"
        f"&start={start}&end={end}&format=JSON&time-standard=LST",
        timeout=120,
    )
    data = _parse(payload)
    if use_cache:
        write_cache("power", key, data)
    return data


def daily_arrays(power: dict) -> dict:
    """Convert the cached payload into numpy arrays plus year/month/doy."""
    dates = power["dates"]
    ts = [dt.date(int(d[:4]), int(d[4:6]), int(d[6:])) for d in dates]
    return {
        "date": np.array([t.isoformat() for t in ts]),
        "year": np.array([t.year for t in ts]),
        "month": np.array([t.month for t in ts]),
        "doy": np.array([t.timetuple().tm_yday for t in ts]),
        "tmax": np.array(power["tmax"], float),
        "tmin": np.array(power["tmin"], float),
        "tdew": np.array(power["tdew"], float),
        "rh": np.array(power["rh"], float),
        "ws": np.array(power["ws"], float),
        "rs": np.array(power["rs"], float),
        "ps": np.array(power["ps"], float),
        "pr": np.array(power["pr"], float),
        "cell": power.get("cell", {}),
    }
