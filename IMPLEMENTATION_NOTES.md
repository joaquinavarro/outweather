# Implementation notes — deviations from the v2.0 spec

This file records every place where the running code departs from
`ROOTSHIFT_SPEC_v2.0_FINAL.md`, with the reason. Nothing here is silent: each item is either a
bug fix, a feasibility constraint, or a modelling decision that the team should ratify.

## Model changes

### 1. `family_gap = 1` instead of 2
The spec (§10.7.3, R2) asks for a two-season separation between crops of the same botanical family.
That rule rejects `corn → soybean → corn`, i.e. the standard US corn–soybean rotation, and the
optimizer responded with agronomically strange sequences. The default is now a one-season gap: the
same family cannot repeat back-to-back, but the canonical rotation is allowed. Configurable in
`domain/rotation.py::Constraints`.

### 2. Production is a relative index, not summed tonnes
Summing tonnes of corn, soybean and alfalfa hay is meaningless (a tonne of hay is not a tonne of
grain). The objective and the headline metrics now use a **relative production index** (mean relative
yield × 100), which is comparable across crops. Tonnes per crop are still reported in the per-season
detail and used for nutrient removal.

### 3. Unmodelled-loss noise
With irrigation assumed to cover the deficit and heat penalties capped, the first build reported a 0%
chance of a bad season — an overconfident claim. A lognormal multiplier (`sigma = 0.12`, mean 1) now
represents hail, pests, lodging and management, which the model does not simulate. It uses common
random numbers, so every candidate rotation is compared under the same draws.

### 4. Cover crops produce nothing
Cereal rye was being selected as a cash crop because it scored well on water. A `cover: true` crop now
occupies the season but contributes zero harvested production.

### 5. Heat and frost factors softened
`f_heat` was capped at 50% loss (`k=0.5`), which halved corn yield in any Kansas summer and pushed the
optimizer away from corn entirely. Now `k=0.25`, floor 0.75 (max 25% loss). `f_frost`: `k=0.5`,
floor 0.5.

### 6. SPEI uses a shifted two-parameter log-logistic
The spec asks for a three-parameter log-logistic fitted by L-moments. The implementation fits a
two-parameter Fisk distribution to the shifted series (`D = P − PET`). It standardises correctly and
is monotone, but it is an approximation, documented in `domain/drought.py`.

### 7. Leaf wetness is a daily proxy
No hourly POWER product is in the project catalog, so LWD uses the dew-point gap plus humidity and
rain, with the MODIS night-LST term as a substitute for radiative cooling. Confidence is capped at
"medium" for disease risk.

### 8. Erosivity from monthly rainfall
The demo fixtures have no IMERG 30-minute data, so the R factor uses the Renard–Freimund monthly
approximation. The EI30 path is the production route.

## Engineering constraints

### 9. No PostGIS in the MVP
Farms live in memory; series are Parquet/JSON. The DDL in the spec stays as the target schema. The
repository layer is isolated so the swap is contained.

### 10. Maps are SVG
MapLibre + TiTiler need raster tiles, which the offline demo cannot serve. The parcel, zones and time
map are SVG rendered from GeoJSON. The data contract is the same; only the renderer changes.

### 11. SSURGO spatial query
`SDA_Get_Mukey_from_intersection_with_SDU` does not exist on the tabular endpoint (verified). The
working query is a `mupolygongeo.STIntersects(geometry::STGeomFromText(...))` predicate on
`mupolygon`. `ma.slope` and `ch.siltotal_r` do not exist either; the real columns are `silttotal_r`
and slope is defaulted to 2% until NASADEM is wired in.

### 12. STATSGO2 fallback not implemented
The chain is SSURGO → default silt loam. STATSGO2 is specified but the SDA call is identical, so it is
a small addition, not a design change.

### 13. Irrigation scoring gives existing equipment a +12 bonus
The first build recommended subsurface drip to a farm that already runs a centre pivot, because the
scoring only compared capital cost and efficiency. Equipment already on the farm is paid for, so the
matrix gives the existing system a +12 point bonus (capped at 100). Materials now follow the chosen
system: pivot spans and sprinkler packages, furrow ditching, or drip laterals and emitters.

## Verification added after the first build

- `tests/test_offline.py` proves that building the context and the full rotation performs zero network
  I/O, and that the provider layer refuses to run with `ROOTSHIFT_OFFLINE=1`.
- `tests/test_api_contract.py` asserts every field the web app reads, per endpoint — a green build with
  blank panels can no longer pass.
- `frontend/tests/ui-check.mjs` drives Chromium through the real UI (landing → farm → simulation → all
  six panels → slider → hazard protocol), fails on any console error or 4xx, and captures the
  screenshots in `docs/screenshots/`.

## PDF and CSV export

The spec promises an "Exportar PDF" per function (3.1, 13.3). The **Rotation** tab now exports:

- `GET /farms/{id}/report.pdf` — two pages: farm header, resilience index and KPIs, rotation table,
  all eight scenarios, nutrient balance, findings, caveats, **data sources with resolution and period**,
  and the attribution/disclaimer footer. Localised (EN/ES).
- `GET /farms/{id}/report.csv` — the same numbers as CSV blocks (`# farm`, `# metrics`, `# rotation`,
  `# scenarios`, `# nutrients`, `# findings`), UTF-8 with BOM so Excel opens it correctly.

Both are generated server-side (reportlab) with `pageCompression=0`, so the text stays extractable and
the tests can assert the title in each language instead of only the MIME type.

### What rendering the PDF revealed

The API tests passed and the PDF was wrong in two ways that only show up when you look at it:

1. **Header cells overlapped.** Plain strings in a reportlab table do not wrap: "Recovery after the
   worst year" ran over "Three dry years in a row". Header cells are now `Paragraph`s.
2. **The data-source row overflowed the column.** The POWER variable list is long
   (`T2M,T2M_MAX,T2M_MIN,…`) and printed on top of the resolution column. Body cells wrap when
   `wrap_body=True`.

Both are the same class of defect as the empty time-map panel in round 3: the tests were green because
they checked that something was returned, not that it was readable.

## Manual rotation editing

`PUT /rotations/{id}` existed but only returned the new sequence and some metrics, so the UI could not
show what an edit costs. It now goes through `farm_service.recompute_rotation`, which re-evaluates the
edited sequence against the **stored baseline** and returns metrics, all scenarios, the IRS, the
nutrient balance, refreshed findings, the delta and the constraint warnings — the same shape as the
optimiser output, so the panel needs no special case.

- The baseline is never overwritten: every edit is compared with the originally optimised rotation,
  not with the previous edit.
- Edits are deterministic (same sequence → same numbers), which the tests assert.
- Hard constraints warn but never block: the farmer can plant what they want, the app just says
  "grain sorghum follows the same plant family (poaceae)".
- *Restore optimised* re-runs the search and replaces the edited rotation.

## Persistence (SQLite instead of PostGIS)

Section 9 of the notes said "no database, everything in memory". That meant an API restart during the
demo wiped every farm, and the report endpoint had nothing left to render.

`rootshift/storage/db.py` adds a two-table SQLite store (stdlib, no server) and the API uses it as a
write-through cache:

- `farm` keeps the id, demo/fixture path, profile, boundary, session and last-rotation pointer.
- `rotation` keeps the full result payload as JSON.
- On a miss, `_hydrate_farm` reloads the fixture from disk and rebuilds the context; `_get_rotation`
  reloads the payload. Nothing in the endpoints changed shape.

Context is **not** stored: it is derived (1.5 s to rebuild) and storing it would duplicate the
fixtures. Rotations are stored because they cost a Monte Carlo run.

`scripts/restart_check.py` proves it for real: it creates a farm, kills the API process, starts a new
one, and reads back the context, the rotation (same IRS, same crops) and the PDF.

PostGIS is still the target (geo queries, multi-tenant); the repository surface is two functions, so the
swap stays contained.

## Real NASA data beyond POWER (Earthdata Login)

With an Earthdata Login token the app now ingests **GPM IMERG monthly (P04)** for the three demo farms.

- `providers/earthdata.py` holds the token (from `EARTHDATA_TOKEN` or the gitignored `backend/.env`),
  CMR granule search and OPeNDAP `.ascii` subsetting.
- `pipeline/ingest_imerg.py` walks 2001-01 → 2024-12, one OPeNDAP request per month with a window that
  covers all three farms, and writes `data/fixtures/imerg_monthly.json` (tracked, 15 KB).
- `services/context.py` uses that series as the **primary precipitation source** for SPI/SPEI and the
  annual statistics; POWER stays as the fallback and for daily extremes.

### Why OPeNDAP and not downloads

A monthly IMERG granule is 19 MB and downloads at ~0.5 MB/s here (35 s). Reading the HDF5 remotely with
h5py costs ~83 s per granule (hundreds of range requests). Through OPeNDAP the same Kansas window
returns in **0.8 s**, so 288 months took **61 s** instead of three hours. That decision is the whole
reason this was feasible.

### What changed in the numbers

Finney's median annual precipitation moved from 536 mm (POWER) to 561 mm (IMERG) and SPEI-12 from
0.78 to 0.27. The drought index is now computed from satellite-gauge precipitation, and every panel
shows the new caveat: *"Monthly precipitation comes from GPM IMERG (real); daily extremes (Rx1day, dry
spells) still come from POWER."*

### Why SMAP is still synthetic

SMAP L4 has **no OPeNDAP endpoint** (`.dds` and `.ascii` return 404) and its granules are ~100 MB on the
NSIDC cloud. Reading one via HTTP range requests takes ~83 s; 3,650 daily granules for 2015–2024 would
be days of work. It stays a fixture, declared as such.

## Running it without a shell script

The original `start.ps1` was the only way to run the whole thing, which is a Windows-only answer to a
cross-platform question. There are now three entry points, all verified:

1. **Docker** — `docker compose up --build`. Multi-stage image: Node builds the static site, Python
   serves it. One container, one port (8000). The SQLite file lives in a named volume so `down` does
   not lose farms.
2. **Python only** — `python -m rootshift` after `npm run build`. The API mounts `frontend/out` at `/`,
   so there is one process and one port and **no Node at runtime**.
3. **Development** — the two-process setup (`npm run dev` + uvicorn `--reload`) with hot reload.

`frontend/lib/api.ts` now defaults `API_BASE` to `""` (same origin); only `npm run dev` overrides it via
`frontend/.env.development`.

### A bug this exposed

Mounting the site on the API showed the time map requesting **GIBS imagery for 1991-01-01**, a date
before MODIS Terra existed. GIBS answered with a blank tile, so it looked fine; the browser fired a
`422` only once the API started validating dates properly.

Three fixes: `/imagery/layers` now publishes each layer's `start`, `/imagery` returns
`DATE_BEFORE_LAYER_START` instead of a blank PNG, and the time map filters its series to the layer's
valid window and starts on the newest date rather than the oldest. There are tests for the guard and
for the first valid day.

## Field selection by drawing a polygon (ported from CTRL-Shift)

The old landing was three demo cards plus a latitude/longitude form. Field selection is now a map with a
polygon tool, ported from the `CTRL-Shift/` project the user provided.

- **Leaflet + react-leaflet** (`components/FieldMap.tsx`, loaded with `ssr: false`): click to add
  vertices, click the first point (or *Close polygon*) to close the ring, drag vertices to edit, search
  by place name or `lat, lon`, and presets for the three demo fields. The area is geodesic
  (`@turf/area`) and updates live.
- **MapLibre GL** (`components/Field3D.tsx`) for the 3D tab: raster basemaps, `raster-dem` terrain from
  open Terrarium tiles, the parcel as a draped fill (default) or a `fill-extrusion` volume, coloured by
  the crop of each rotation year, with orbit and camera presets.
- **Backend**: `POST /api/v1/farms` now accepts `boundary` (GeoJSON ring, `[lon, lat]`). The polygon is
  validated (≥3 vertices, inside the US pilot, 0.5–5000 ha), its geodesic area and centroid are computed
  and the fixture is built for the centroid while storing the drawn ring as the farm boundary. The
  demo-farms endpoint now publishes each demo boundary so the presets can draw them.

### Two bugs the integration exposed

1. **The MapLibre worker would not load.** Next bundles the library but not its worker; the reference
   project solved it with a public copy. Doing that here failed too: Starlette served
   `maplibre-gl-worker.mjs` as `text/plain`, because Python's `mimetypes` does not know `.mjs` on
   Windows, and browsers reject a module worker served with the wrong type. Fixed by
   `mimetypes.add_type("text/javascript", ".mjs")` in the API and a `prebuild` step that copies the
   worker into `public/`.
2. **The tiles needed an API key.** CARTO's public basemap now watermarks requests without a key
   ("API KEY REQUIRED"). Switched to Esri World Imagery (satellite, no key) and Esri Dark Gray Canvas,
   which also show real field boundaries instead of a grey grid.

### What changed in the data path

A drawn field is a *real* custom field: the backend reverse-geocodes the centroid, fetches NASA POWER
1991–2024 and SSURGO for that point, and stores the drawn ring. Measured on a 121 ha field near Garden
City: 10.6 s end to end, county Finney, silt loam. Demo presets keep using the preloaded fixtures so the
offline demo still works.

## Three-step flow and a five-section navbar

The app was restructured from "landing → dashboard with 7 tabs" to four screens, per a direct design
request:

1. **Map** — full-screen satellite map; only a title, a search box and a minimal toolbar (pencil to
   draw, bin to clear, hectares readout). The demo fields are header chips. No description, no
   side panel.
2. **Design** — the user picks their current crop, water regime and the crops they want to plant; the
   crops recommended for the region (from `regions/us_ks.yaml`) are listed as "proposed". *Analyse*
   moved here from the map.
3. **Loading** — a bare spinner, no text or logo.
4. **Results** — navbar of five sections: *Resumen, Rotación, Riego, Sanidad, Riesgos*.

### Resumen is synthesised, and the 3D parcel is inside it

- *Resumen* leads with the IRS gauge and three primary KPIs (production index, bad-season chance,
  SPEI-12); everything harder to read (index breakdown, findings, current conditions, caveats) is
  behind a native `<details>` "Show details".
- The **3D parcel** (MapLibre) sits inside *Resumen*. It is always draped on the terrain over
  satellite imagery with relief on; the only map controls are *Orbit* and *Centre*. A **time bar**
  walks the historical years (2001–2024) and recolours the parcel by that year's SPEI-12 severity, so
  the "time map" is no longer pixelated GIBS imagery but the same 3D parcel seen across past years.
  (The GIBS `/imagery` endpoints remain for the API contract, but the UI no longer renders them.)

### What this replaces

- The two-column landing (map + sidebar with "Analyse this field") is gone.
- The separate *Time map* and *3D field* tabs are gone; both merged into *Resumen*'s 3D parcel.
- `Field3D` lost the extrusion/dark-map/terrain toggles and the crop-year colouring; the time bar and
  SPEI colour scale replaced them.

## What is still missing against the spec

- CoCoRaHS validation, OpenET, SMAP, MODIS and GLDAS **analytics** providers: the clients are not wired
  yet; the fixtures stand in for them. IMERG (below) and GIBS imagery are real.
- PostGIS (SQLite stands in, see the persistence section).
- Drag-and-drop for the edit: the interaction is click → select, which is keyboard-accessible and
  works on touch; real drag-and-drop would be a nicety, not a capability.

## Bilingual UI (D16)

`en-US` is the default and `es-ES` is fully supported: header toggle, persisted in `localStorage`,
`<html lang>` updated, and `Accept-Language` / `?locale=` honoured by the API.

Localising only the shell would have left the product half-translated, so the content is localised too:

- UI strings live in `frontend/lib/i18n.ts` (~150 keys, `t(key, vars)`).
- Findings come from the engine as **code + params**, and the UI renders them. The English `text` is
  still returned for API consumers, but the Spanish version is built from `finding.WATER_GAP_COVERED`
  and `{pct}`, so a number can never disagree between languages.
- Caveats carry a **code** (`SYNTHETIC_SATELLITES`, `NOT_A_DIAGNOSIS`, …) alongside the English text.
- Catalog content ships as `crops_es.yaml`, `diseases_es.yaml` and `hazards_es.yaml`, keyed by id. The
  English catalogs stay untouched, so the engine and its tests keep reading English.
- Irrigation system names and material items carry `name_es` / `item_es`.
- IRS labels are a `label_code` (`highly_resilient`, …) that both languages map.

Tests assert that **every** crop, disease and hazard has Spanish text and that the step counts match,
so a new catalog entry without translation fails the build instead of silently falling back.

## Two numeric inconsistencies fixed while localising

1. **Flood return period contradicted its own probability.** The card showed "13%/yr · 577-year return
   period": the probability came from a p90 threshold but the period was fitted to the maximum value.
   Now `T = 1/p`, so 13%/yr is an 8-year period.
2. **The chart ignored the caveat.** The panel says return periods are capped at 50 years with 24 years
   of record, but nothing capped them. `hazards._cap` now enforces the limit, and a test asserts it.

## Real satellite imagery for F4 (NASA GIBS, P23)

The time map was showing a modelled sparkline and a coloured parcel. It now shows the **real field from
MODIS**, served by NASA GIBS over WMS with no authentication.

- `providers/gibs.py` builds WMS 1.3.0 requests. **Trap:** with `CRS=EPSG:4326`, WMS 1.3.0 expects the
  BBOX in **lat,lon** order. Passing lon,lat returns a valid PNG of the wrong place (or a blank one) with
  HTTP 200, so it fails silently.
- Verified layers: `MODIS_Terra_L3_NDVI_16Day`, `MODIS_Terra_L3_NDVI_Monthly`,
  `MODIS_Terra_CorrectedReflectance_TrueColor`, `MODIS_Terra_L3_Land_Surface_Temp_8Day_Day`.
  The names must come from `GetCapabilities` (2,969 layers); plausible names such as
  `MODIS_Terra_NDVI_8Day` return a transparent image instead of an error.
- The API proxies and caches the PNG (`/api/v1/imagery`), so the browser never talks to GIBS and the
  second view is instant.
- The view is deliberately **county scale** (≥ 0.12° wide) with the field outlined: MODIS is 250–500 m,
  and zooming to the parcel turns the image into a handful of giant blocks. This makes the resolution
  limit of §7.5 visible rather than hiding it.
- Offline, the image request fails and the panel falls back to the modelled parcel with an explicit note.

GIBS is **not** in the original 22-product catalog. It was added as **P23** in the spec (§7.2) with an
explicit note: it is visualisation only and never enters a calculation.

## What the first imagery build got wrong

Two defects that only appeared in the browser, not in the API tests:

1. `POST /farms` returned a summary without `boundary`, so the time map had no bbox and rendered an empty
   panel. Fixed by returning `boundary`, `location` and `irrigation` in the summary (and asserted in the
   contract test).
2. The headless check screenshotted the tab 700 ms after clicking, before GIBS answered. The test now
   waits for `img.complete && naturalWidth > 0` and fails if the image does not come from the API proxy.

## Custom fields (added after the first build)

The spec makes the polygon the primary input (D1 = B), so the app now accepts coordinates instead of
only the pre-baked demo fields.

- `POST /api/v1/farms` accepts `latitude`, `longitude`, `area_ha`, `irrigation_status`,
  `irrigation_system` and `current_crop_id` as an alternative to `demo_farm_id`.
- A square parcel of the requested area is built around the point
  (`services/fixture_builder.polygon_from_center`, area verified against the spherical excess).
- The county is resolved with Nominatim reverse geocoding and mapped to a SSURGO areasymbol through
  `data/catalog/counties_us.yaml`, generated from SSURGO's own `legend` table for KS, NE, OK and CO
  (353 counties). The direct spatial alternative — `mupolygon.STIntersects` without an `areasymbol`
  filter — was measured at more than two minutes and is not usable interactively.
- The built fixture is cached in `data/cache/custom_<hash>.json`, so a repeat visit is instant.
- Limits: CONUS bounding box and the four states in the index. Outside that, the API returns
  `LOCATION_OUT_OF_US`, `COUNTY_NOT_IN_PILOT` or `STATE_NOT_IN_PILOT`.

## Known duplication

`pipeline/build_fixtures.py` keeps its own copy of the synthetic-layer generator because the demo
fixtures are frozen artifacts used by the screenshots and the golden expectations. The custom-field
path uses `services/fixture_builder.synthesize`. They must be kept in sync until the demo fixtures are
regenerated from the shared function.

## Rotation coherence (current crop → first season, preferred crops guaranteed)

The design panel used to treat the "crops you want to plant" selection as a soft hint, so the proposed
rotation could contain crops the farmer never picked, and the crop they already have could appear
anywhere (or not at all). That contradicted the whole premise of the simulator.

- `domain/rotation.py::Constraints` now carries `first_crop`. When the farmer has a crop, it is pinned
  to season one; when they choose **None** (empty current-crop list), no crop is pinned.
- `must_include` (the preferred selection) is now a **hard** constraint, not a 0.85 score penalty. The
  beam search uses a lookahead that reserves the last seasons for any required crop not yet placed, so
  every selected crop is guaranteed to appear at least once.
- The current crop and every selected crop are always kept in the candidate pool even when
  water-stressed, so the app models what the farmer actually has and lets the lower yield speak for
  itself rather than silently dropping the choice.
- `services/farm_service.build_rotation` derives `first_crop` from `farm.current_crops`, dedupes the
  preferred list, removes the pinned crop and exclusions, and raises the distinct-species cap (max 6)
  if the farmer's selections need it. When the farmer selected **None**, the baseline becomes a
  monoculture of the first preferred crop (or the region's first crop if nothing was selected), so the
  "now vs current" comparison stays readable.
- `POST /farms` now accepts an empty `current_crop_id` ("None"); `fixture_builder` turns it into an
  empty `current_crops` list, and the context builder already tolerated an empty list.
- With "None" planted there is no current crop to anchor the irrigation design on, so `F3` falls back
  to the first preferred crop, then to the region's first crop, for the season window and Kc curve
  (this also fixed a `current_crops[0]` IndexError / HTTP 500). The regression is covered by
  `tests/test_none_crop.py`, which also asserts the pinned first season and the guaranteed preferred
  crops.

## Disease panel shows every selected crop, not just the current one

`GET /diseases` only ever listed the farm's `current_crops`, so selecting several preferred crops still
showed a single crop. The disease panel now covers **every crop the farmer selected for the farm**: the
crop from the design dropdown plus the preferred crops ticked under the recommendations.

- `disease_report` takes the farm `profile`: with no explicit crop list it defaults to
  `current_crops + must_include`; with an explicit list it uses that list. This keeps the fix working
  even for a build of the web app that calls the endpoint without `crop_id`.
- The web app also computes the selection (current crop + preferred) and passes it explicitly, so the
  panel is independent of the optimiser. If nothing is selected the tab shows a short prompt instead of
  a blank table.
- Crops with no disease in the catalog (covers, oats, sunflower, canola) are skipped rather than
  rendered as empty tables.

## Overview surfaces the resilience gain at a glance

*Resumen* now leads with the IRS delta against the current rotation ("+N resilience vs current") and a
2×2 comparison of production index, bad-season chance, recovery and three-dry-years probability, each
with its "before" value and a ▲/▼ arrow. The single SPEI-12 chip was dropped from the hero (SPEI still
appears in the 3D time bar and the hazards panel); the point of the hero is now "how much less
vulnerable this rotation is", not a climate reading.

