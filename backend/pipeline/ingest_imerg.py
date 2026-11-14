"""Ingest real GPM IMERG monthly precipitation for the demo farms (P04).

Uses OPeNDAP subsetting over Earthdata Login, so each month costs one small
request instead of a 19 MB granule download.

Usage:
    python -m pipeline.ingest_imerg                 # 2001-2024, demo farms
    python -m pipeline.ingest_imerg --from 2015 --to 2024
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rootshift import catalog, config
from rootshift.providers import earthdata

PRODUCT = "GPM_3IMERGM.07"
BASE = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/{product}/{year}/{filename}"
# fixtures are tracked in git: the demo must work on a fresh clone and offline
CACHE = Path(config.FIXTURES_DIR) / "imerg_monthly.json"


def grid_index(lat: float, lon: float) -> tuple[int, int]:
    """0.1-degree IMERG grid: lat starts at -89.95, lon at -179.95."""
    return round((lat + 89.95) / 0.1), round((lon + 179.95) / 0.1)


def granule_url(year: int, month: int) -> str:
    filename = f"3B-MO.MS.MRG.3IMERG.{year}{month:02d}01-S000000-E235959.{month:02d}.V07B.HDF5"
    return BASE.format(product=PRODUCT, year=year, filename=filename)


def farms() -> list[dict]:
    out = []
    for region in catalog.regions().values():
        for farm in region.demo_farms:
            out.append({"id": farm.id, "lat": farm.location["lat"], "lon": farm.location["lon"]})
    return out


def fetch_month(year: int, month: int, window: tuple[int, int, int, int], farms_list: list[dict], retries: int = 3) -> dict:
    lon_min, lon_max, lat_min, lat_max = window
    constraint = f"precipitation[0:0][{lon_min}:{lon_max}][{lat_min}:{lat_max}]"
    url = granule_url(year, month)

    last_error = None
    for attempt in range(retries):
        try:
            parsed = earthdata.opendap_ascii(url, constraint)
            rows = parsed["precipitation"]
            days = calendar.monthrange(year, month)[1]
            values = {}
            for farm in farms_list:
                lat_idx, lon_idx = grid_index(farm["lat"], farm["lon"])
                j = lon_idx - lon_min
                k = lat_idx - lat_min
                try:
                    rate = rows[j][k]  # mm/hour
                except IndexError:
                    rate = float("nan")
                values[farm["id"]] = round(rate * 24.0 * days, 2) if rate == rate else None
            return {"month": f"{year}-{month:02d}", "values": values}
        except Exception as exc:  # network hiccup, rate limit
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    return {"month": f"{year}-{month:02d}", "values": None, "error": str(last_error)[:160]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="start", type=int, default=2001)
    parser.add_argument("--to", dest="end", type=int, default=2024)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    if not earthdata.has_token():
        raise SystemExit("EARTHDATA_TOKEN is not configured (backend/.env)")

    farms_list = farms()
    indexes = {f["id"]: grid_index(f["lat"], f["lon"]) for f in farms_list}
    lats = [v[0] for v in indexes.values()]
    lons = [v[1] for v in indexes.values()]
    window = (min(lons) - 1, max(lons) + 1, min(lats) - 1, max(lats) + 1)
    print(f"farms: {list(indexes)} | grid window lon {window[0]}..{window[1]} lat {window[2]}..{window[3]}")

    jobs = [(y, m) for y in range(args.start, args.end + 1) for m in range(1, 13)]
    print(f"months to fetch: {len(jobs)}")

    results: dict[str, dict] = {}
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_month, y, m, window, farms_list): (y, m) for y, m in jobs}
        done = 0
        for future in as_completed(futures):
            row = future.result()
            results[row["month"]] = row
            done += 1
            if done % 24 == 0 or done == len(jobs):
                elapsed = time.time() - started
                print(f"  {done}/{len(jobs)} months · {elapsed:.0f}s · eta {elapsed / done * (len(jobs) - done):.0f}s")

    months = sorted(results)
    failed = [m for m in months if results[m].get("values") is None]
    payload = {
        "source": "NASA GPM IMERGM v07 (monthly, 0.1 deg) via OPeNDAP",
        "product": "GPM_3IMERGM",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "grid": {"lat0": -89.95, "lon0": -179.95, "step": 0.1},
        "months": months,
        "failed_months": failed,
        "farms": {
            farm["id"]: {
                "lat": farm["lat"],
                "lon": farm["lon"],
                "indices": list(indexes[farm["id"]]),
                "mm": [results[m]["values"][farm["id"]] if results[m].get("values") else None for m in months],
            }
            for farm in farms_list
        },
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"wrote {CACHE} ({CACHE.stat().st_size/1024:.0f} KB) | failed months: {len(failed)}")


if __name__ == "__main__":
    main()
