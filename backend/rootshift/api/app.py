"""FastAPI application (spec 11)."""

from __future__ import annotations

import json
import mimetypes
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

# Windows does not map .mjs by default; a module worker served as text/plain is
# rejected by the browser. Register it before StaticFiles starts guessing types.
mimetypes.add_type("text/javascript", ".mjs")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from .. import catalog, config
from ..domain import rotation as rotation_mod
from ..providers import gibs
from ..services import context as context_service
from ..services import farm_service
from ..services import fixture_builder
from ..services import reporting
from ..storage import db as storage

app = FastAPI(title="ROOTSHIFT API", version=config.MODEL_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FARMS: dict[str, dict] = {}
ROTATIONS: dict[str, dict] = {}
JOBS: dict[str, dict] = {}
EXECUTOR = ThreadPoolExecutor(max_workers=4)


# --------------------------------------------------------------------------
# schemas
# --------------------------------------------------------------------------

class FarmCreate(BaseModel):
    name: str | None = None
    demo_farm_id: str | None = None
    # custom field path (needs internet: POWER + SSURGO)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_ha: float | None = Field(default=None, gt=0, le=5000)
    irrigation_status: str = "rainfed"
    irrigation_system: str = "none"
    current_crop_id: str | None = None
    objective: str = "balanced"
    risk_tolerance: str = "medium"
    horizon_seasons: int = Field(default=8, ge=4, le=12)
    max_crops: int = Field(default=4, ge=2, le=6)
    must_include: list[str] = []
    excluded_crops: list[str] = []
    boundary: list[list[float]] | None = None


class RotationUpdate(BaseModel):
    sequence: list[str]


class IrrigationRequest(BaseModel):
    flow_l_s: float | None = None
    annual_limit_m3: float | None = None
    hours_per_day: float | None = None


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def envelope(data: Any, context: dict | None = None, **extra) -> dict:
    meta = {
        "request_id": "req_" + uuid.uuid4().hex[:12],
        "model_version": config.MODEL_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data_mode": config.data_mode(),
    }
    if context:
        meta["confidence"] = context.get("confidence")
        meta["caveats"] = context.get("caveats", [])
    meta.update(extra)
    return {"data": data, "meta": meta}


def get_farm_or_404(farm_id: str, request: Request) -> dict:
    farm = FARMS.get(farm_id) or _hydrate_farm(farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "farm not found"})
    session = request.cookies.get("rs_session")
    if farm.get("session_id") and session and farm["session_id"] != session:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "farm not found"})
    return farm


def _hydrate_farm(farm_id: str) -> dict | None:
    """Reload a farm from SQLite after a restart and rebuild its context."""
    record = storage.get_store().get_farm(farm_id)
    if not record:
        return None
    path = record.get("fixture_path")
    if not path or not Path(path).exists():
        return None
    fixture = json.loads(Path(path).read_text(encoding="utf-8"))
    context = context_service.build_context(fixture, record["profile"])
    farm = {**record, "context": context}
    FARMS[farm_id] = farm
    return farm


def _get_rotation(rotation_id: str) -> dict | None:
    result = ROTATIONS.get(rotation_id)
    if result:
        return result
    stored = storage.get_store().get_rotation(rotation_id)
    if stored:
        ROTATIONS[rotation_id] = stored
    return stored


def _locale(request: Request) -> str:
    """Locale from ?locale= (es-ES|en-US) or Accept-Language. Defaults to en-US (D16)."""
    query = request.query_params.get("locale")
    if query:
        return "es-ES" if query.lower().startswith("es") else "en-US"
    header = (request.headers.get("accept-language") or "").lower()
    return "es-ES" if header.startswith("es") else "en-US"


def run_job(kind: str, fn, *args, **kwargs) -> str:
    job_id = "job_" + uuid.uuid4().hex[:10]
    JOBS[job_id] = {"job_id": job_id, "status": "queued", "progress": 0.0, "stage": "queued", "result": None}

    def worker():
        JOBS[job_id].update({"status": "running", "progress": 0.15, "stage": f"running {kind}"})
        try:
            result = fn(*args, **kwargs)
            JOBS[job_id].update({"status": "done", "progress": 1.0, "stage": "done", "result": result})
        except Exception as exc:  # surface the message to the UI
            JOBS[job_id].update({"status": "failed", "progress": 1.0, "stage": "failed", "error": str(exc)})

    EXECUTOR.submit(worker)
    return job_id


# --------------------------------------------------------------------------
# meta
# --------------------------------------------------------------------------

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": config.MODEL_VERSION, "data_mode": config.data_mode()}


@app.get("/api/v1/meta/sources")
def meta_sources():
    return envelope(catalog.sources())


@app.get("/api/v1/meta/region")
def meta_region():
    reg = catalog.region()
    return envelope(
        {
            "id": reg.id,
            "name": reg.name,
            "seasons_per_year": reg.seasons_per_year,
            "counties": reg.counties,
            "crops": reg.crops,
            "demo_farms": context_service.available_demo_farms(),
        }
    )


@app.get("/api/v1/catalog/crops")
def catalog_crops():
    return envelope(
        [
            {
                "crop_id": c.id,
                "name_en": c.name_en,
                "name_es": catalog.crop_name(c.id, "es-ES"),
                "family": c.family,
                "is_legume": c.is_legume,
                "cycle_type": c.cycle_type,
                "kc_mid": c.kc_mid,
                "season_length_days": c.season_length_days,
            }
            for c in catalog.crops().values()
        ]
    )


# --------------------------------------------------------------------------
# farms
# --------------------------------------------------------------------------

@app.post("/api/v1/farms")
def create_farm(payload: FarmCreate, request: Request):
    started = time.time()
    demo_id = payload.demo_farm_id

    if not demo_id:
        drawn = None
        if payload.boundary and len(payload.boundary) >= 3:
            # the farmer drew the field on the map: the polygon is the source of truth
            try:
                drawn = fixture_builder.normalise_ring(payload.boundary)
            except ValueError as exc:
                raise HTTPException(422, {"code": str(exc).split(":", 1)[0], "message": str(exc)})
            lat, lon = fixture_builder.polygon_centroid(drawn)
            area_ha = fixture_builder.polygon_area_ha(drawn)
        elif payload.latitude is not None and payload.longitude is not None and payload.area_ha is not None:
            lat, lon, area_ha = payload.latitude, payload.longitude, payload.area_ha
        else:
            raise HTTPException(
                400,
                {
                    "code": "VALIDATION_ERROR",
                    "message": "provide demo_farm_id, a drawn boundary polygon, or latitude + longitude + area_ha",
                },
            )
        try:
            fixture = fixture_builder.build_custom_fixture(
                lat,
                lon,
                area_ha,
                payload.name or "",
                irrigation_status=payload.irrigation_status,
                irrigation_system=payload.irrigation_system,
                current_crop_id=payload.current_crop_id,
                ring=drawn,
            )
        except ValueError as exc:
            code = str(exc).split(":", 1)[0]
            raise HTTPException(422, {"code": code, "message": str(exc)})
        except Exception as exc:  # upstream provider failure
            raise HTTPException(502, {"code": "UPSTREAM_ERROR", "message": str(exc)})
        demo_id = fixture["farm"]["id"]
        context_service.register_fixture(demo_id, fixture)
        context_service._load_fixture_from_disk.cache_clear()

    try:
        fixture = farm_service.get_fixture(demo_id)
    except KeyError:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": f"unknown demo farm {demo_id}"})

    profile = farm_service._profile_from_fixture(fixture)
    profile.update(
        {
            "objective": payload.objective,
            "risk_tolerance": payload.risk_tolerance,
            "horizon_seasons": payload.horizon_seasons,
            "max_crops": payload.max_crops,
            "must_include": payload.must_include,
            "excluded_crops": payload.excluded_crops,
        }
    )

    context = context_service.build_context(fixture, profile)
    farm_id = "frm_" + uuid.uuid4().hex[:10]
    fixture_path = (
        fixture.get("meta", {}).get("cache_path")
        or str(config.FIXTURES_DIR / f"{demo_id}.json")
    )
    record = {
        "farm_id": farm_id,
        "demo_id": demo_id,
        "fixture_path": fixture_path,
        "profile": profile,
        "context": context,
        "boundary": context["farm"].get("boundary"),
        "session_id": request.cookies.get("rs_session"),
        "created_at": time.time(),
    }
    FARMS[farm_id] = record
    storage.get_store().save_farm(
        {
            "farm_id": farm_id,
            "demo_id": demo_id,
            "fixture_path": fixture_path,
            "profile": profile,
            "boundary": context["farm"].get("boundary"),
            "session_id": request.cookies.get("rs_session"),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    summary = {
        "farm_id": farm_id,
        "name": context["farm"]["name"],
        "area_ha": context["area_ha"],
        "county": context["farm"].get("county"),
        "label": context["farm"].get("label"),
        "boundary": context["farm"].get("boundary"),
        "location": context["farm"].get("location"),
        "irrigation": context["farm"].get("irrigation"),
        "confidence": context["confidence"],
        "caveats": context["caveats"],
        "caveat_codes": context.get("caveat_codes", []),
        "synthetic": context["synthetic"],
        "build_ms": int((time.time() - started) * 1000),
    }
    response = JSONResponse(envelope(summary, context), status_code=201)
    if not request.cookies.get("rs_session"):
        response.set_cookie("rs_session", uuid.uuid4().hex, httponly=True, samesite="lax", max_age=30 * 24 * 3600)
    return response


@app.get("/api/v1/farms/{farm_id}")
def read_farm(farm_id: str, request: Request):
    farm = get_farm_or_404(farm_id, request)
    ctx = farm["context"]
    return envelope(
        {
            "farm_id": farm_id,
            "name": ctx["farm"]["name"],
            "profile": farm["profile"],
            "boundary": ctx["farm"]["boundary"],
            "area_ha": ctx["area_ha"],
            "confidence": ctx["confidence"],
        },
        ctx,
    )


@app.get("/api/v1/farms/{farm_id}/context")
def read_context(farm_id: str, request: Request):
    farm = get_farm_or_404(farm_id, request)
    ctx = farm["context"]
    return envelope(
        {
            "farm": {
                key: ctx["farm"][key]
                for key in (
                    "id",
                    "name",
                    "county",
                    "label",
                    "area_ha",
                    "production_system",
                    "boundary",
                    "location",
                    "irrigation",
                    "current_crops",
                )
                if key in ctx["farm"]
            },
            "pr_source": ctx.get("pr_source"),
            "region": ctx["region"],
            "climate": ctx["climate"],
            "soil": ctx["soil"],
            "drought": ctx["drought"],
            "water": ctx["water"],
            "carbon": ctx["carbon"],
            "erosion": ctx["erosion"],
            "ndvi": ctx["ndvi"],
            "groundwater": ctx["groundwater"],
            "confidence": ctx["confidence"],
            "caveats": ctx["caveats"],
            "caveat_codes": ctx.get("caveat_codes", []),
            "crops": [
                {
                    "crop_id": cid,
                    "name_en": crop["name_en"],
                    "name_es": crop["name_es"],
                    "family": crop["family"],
                    "is_legume": crop["is_legume"],
                    "cover": crop["cover"],
                }
                for cid, crop in ctx["crops_by_id"].items()
            ],
            "provenance": context_service.provenance_for(ctx),
        },
        ctx,
    )


@app.get("/api/v1/farms/{farm_id}/soil")
def read_soil(farm_id: str, request: Request):
    farm = get_farm_or_404(farm_id, request)
    return envelope(farm["context"]["soil"])


# --------------------------------------------------------------------------
# F1 rotation
# --------------------------------------------------------------------------

@app.post("/api/v1/farms/{farm_id}/rotation:optimize")
def optimize_rotation(farm_id: str, request: Request):
    farm = get_farm_or_404(farm_id, request)
    ctx = farm["context"]

    def compute():
        result = farm_service.build_rotation(ctx, farm["profile"])
        rot_id = "rot_" + uuid.uuid4().hex[:8]
        ROTATIONS[rot_id] = result
        result["rotation_id"] = rot_id
        FARMS[farm_id]["last_rotation_id"] = rot_id
        store = storage.get_store()
        store.save_rotation(rot_id, farm_id, result)
        store.set_last_rotation(farm_id, rot_id)
        return {"rotation_id": rot_id, "result": result}

    job_id = run_job("rotation", compute)
    return JSONResponse(envelope({"job_id": job_id, "status": "queued"}), status_code=202)


@app.get("/api/v1/farms/{farm_id}/rotations/{rotation_id}")
def read_rotation(farm_id: str, rotation_id: str, request: Request):
    get_farm_or_404(farm_id, request)
    result = _get_rotation(rotation_id)
    if not result:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "rotation not found"})
    return envelope(result)


@app.put("/api/v1/farms/{farm_id}/rotations/{rotation_id}")
def update_rotation(farm_id: str, rotation_id: str, payload: RotationUpdate, request: Request):
    farm = get_farm_or_404(farm_id, request)
    base = _get_rotation(rotation_id)
    if not base:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "rotation not found"})
    if not payload.sequence:
        raise HTTPException(400, {"code": "VALIDATION_ERROR", "message": "empty sequence"})

    try:
        updated = farm_service.recompute_rotation(farm["context"], base, payload.sequence)
    except ValueError as exc:
        raise HTTPException(400, {"code": "VALIDATION_ERROR", "message": str(exc)})

    updated["rotation_id"] = rotation_id
    return envelope(updated)


@app.get("/api/v1/farms/{farm_id}/nutrients")
def read_nutrients(farm_id: str, rotation_id: str | None = None, request: Request = None):
    farm = get_farm_or_404(farm_id, request)
    ctx = farm["context"]
    result = ROTATIONS.get(rotation_id) if rotation_id else None
    if not result:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "rotation not found"})
    return envelope(result["nutrients"])


# --------------------------------------------------------------------------
# F2 / F3 / F5
# --------------------------------------------------------------------------

@app.get("/api/v1/farms/{farm_id}/diseases")
def read_diseases(farm_id: str, crop_id: list[str] | None = None, request: Request = None):
    farm = get_farm_or_404(farm_id, request)
    return envelope(
        farm_service.disease_report(
            farm["context"], crop_id, _locale(request), profile=farm.get("profile")
        )
    )


@app.post("/api/v1/farms/{farm_id}/irrigation")
def irrigation(farm_id: str, payload: IrrigationRequest, request: Request):
    farm = get_farm_or_404(farm_id, request)
    ctx = farm["context"]
    irrigation_cfg = ctx["farm"].get("irrigation", {})
    override = {k: v for k, v in payload.model_dump().items() if v is not None}
    if override:
        irrigation_cfg = {**irrigation_cfg, **override}
        ctx = {**ctx, "farm": {**ctx["farm"], "irrigation": irrigation_cfg}}
    return envelope(farm_service.irrigation_report(ctx, profile=farm.get("profile")))


@app.get("/api/v1/farms/{farm_id}/hazards")
def hazards(farm_id: str, request: Request):
    farm = get_farm_or_404(farm_id, request)
    return envelope(farm_service.hazards_report(farm["context"], _locale(request)))


@app.get("/api/v1/farms/{farm_id}/hazards/{hazard_id}/playbook")
def playbook(farm_id: str, hazard_id: str, request: Request):
    get_farm_or_404(farm_id, request)
    try:
        loc = catalog.hazard_localised(hazard_id, _locale(request))
    except KeyError:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "hazard not found"})
    hz = catalog.hazard(hazard_id)
    return envelope(
        {
            "hazard": hz["id"],
            "name": loc["name"],
            "calculable": hz["calculable"],
            "playbook": loc["playbook"],
            "source": hz["source"],
            "locale": loc["locale"],
        }
    )


@app.get("/api/v1/farms/{farm_id}/operations")
def operations(farm_id: str, month: int | None = None, request: Request = None):
    farm = get_farm_or_404(farm_id, request)
    report = farm_service.hazards_report(farm["context"])
    work = report["workability"]
    if month:
        work = {**work, "windows": [w for w in work["windows"] if w["month"] == month]}
    return envelope(work)


# --------------------------------------------------------------------------
# F4 timeline
# --------------------------------------------------------------------------

@app.get("/api/v1/farms/{farm_id}/timeline")
def timeline(farm_id: str, layer: str = "ndvi", request: Request = None):
    farm = get_farm_or_404(farm_id, request)
    ctx = farm["context"]
    arrays = ctx["arrays"]
    series = {
        "ndvi": (ctx["arrays"]["ndvi"] if "ndvi" in ctx["arrays"] else None),
    }
    synthetic = farm_service.get_fixture(farm["demo_id"])["synthetic"]

    if layer == "ndvi":
        values = synthetic["ndvi_daily"]
    elif layer == "soil_moisture":
        values = synthetic["sm_rz"]
    elif layer == "lst_night":
        values = synthetic["lst_night_c"]
    elif layer == "precipitation":
        values = [float(v) for v in arrays["pr"]]
    else:
        raise HTTPException(400, {"code": "VALIDATION_ERROR", "message": f"unknown layer {layer}"})

    dates = arrays["date"]
    points = []
    # monthly means
    buckets: dict[str, list[float]] = {}
    for d, v in zip(dates, values):
        key = f"{d[:4]}-{d[4:6]}"
        buckets.setdefault(key, []).append(float(v))
    for key in sorted(buckets):
        vals = buckets[key]
        points.append({"t": key, "mean": round(sum(vals) / len(vals), 4), "min": round(min(vals), 4), "max": round(max(vals), 4)})

    return envelope(
        {
            "layer": layer,
            "unit": {"ndvi": "index", "soil_moisture": "m3/m3", "lst_night": "degC", "precipitation": "mm/day"}.get(layer),
            "points": points,
            "available_range": {"from": points[0]["t"], "to": points[-1]["t"]} if points else None,
        }
    )


# --------------------------------------------------------------------------
# reports (PDF / CSV)
# --------------------------------------------------------------------------

def _resolve_rotation(farm: dict, rotation_id: str | None) -> dict:
    rid = rotation_id or farm.get("last_rotation_id")
    if not rid:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "no computed rotation for this farm"})
    rotation = _get_rotation(rid)
    if not rotation:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "no computed rotation for this farm"})
    return rotation


def _safe_filename(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " -_" else "" for c in (name or "field")).strip()
    return (cleaned or "field").replace(" ", "-").lower()


@app.get("/api/v1/farms/{farm_id}/report.pdf")
def report_pdf(farm_id: str, rotation_id: str | None = None, request: Request = None):
    farm = get_farm_or_404(farm_id, request)
    rotation = _resolve_rotation(farm, rotation_id)
    locale = _locale(request)
    try:
        payload = reporting.build_pdf(farm["context"], rotation, locale)
    except Exception as exc:
        raise HTTPException(500, {"code": "REPORT_FAILED", "message": str(exc)})
    filename = f"rootshift-{_safe_filename(farm['context']['farm']['name'])}.pdf"
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Language": locale,
        },
    )


@app.get("/api/v1/farms/{farm_id}/report.csv")
def report_csv(farm_id: str, rotation_id: str | None = None, request: Request = None):
    farm = get_farm_or_404(farm_id, request)
    rotation = _resolve_rotation(farm, rotation_id)
    locale = _locale(request)
    payload = reporting.build_csv(farm["context"], rotation, locale)
    filename = f"rootshift-{_safe_filename(farm['context']['farm']['name'])}.csv"
    return Response(
        content=payload.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Language": locale,
        },
    )


# --------------------------------------------------------------------------
# imagery (NASA GIBS) — real satellite images for the time map
# --------------------------------------------------------------------------

@app.get("/api/v1/imagery/layers")
def imagery_layers():
    return envelope(
        {
            "layers": gibs.layers_metadata(),
            "attribution": "NASA GIBS (Global Imagery Browse Services)",
            "note": "Visualisation only; the numeric series comes from the analytics path.",
        }
    )


@app.get("/api/v1/imagery")
def imagery(layer: str, date: str, bbox: str, width: int = 640, height: int = 420):
    try:
        float_parts = [float(v) for v in bbox.split(",")]
        if len(float_parts) != 4 or not all(-180 <= v <= 180 for v in float_parts):
            raise ValueError
        min_lon, min_lat, max_lon, max_lat = float_parts
        if not (min_lon < max_lon and min_lat < max_lat):
            raise ValueError
    except ValueError:
        raise HTTPException(400, {"code": "VALIDATION_ERROR", "message": "bbox must be minLon,minLat,maxLon,maxLat"})

    if layer not in gibs.LAYERS:
        raise HTTPException(400, {"code": "VALIDATION_ERROR", "message": f"unknown layer {layer}"})
    time.strptime(date, "%Y-%m-%d")
    layer_start = gibs.LAYERS[layer]["start"]
    if date < layer_start:
        raise HTTPException(
            422,
            {
                "code": "DATE_BEFORE_LAYER_START",
                "message": f"{layer} imagery starts on {layer_start}; {date} is outside the archive.",
                "layer_start": layer_start,
            },
        )

    width = max(128, min(1280, width))
    height = max(128, min(1280, height))

    try:
        data = gibs.fetch_image(layer, date, bbox, width, height)
    except Exception as exc:
        raise HTTPException(503, {"code": "IMAGERY_UNAVAILABLE", "message": str(exc)})

    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400", "X-Imagery-Source": "NASA GIBS"},
    )


# --------------------------------------------------------------------------
# jobs
# --------------------------------------------------------------------------

@app.get("/api/v1/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "job not found"})
    payload = {k: job[k] for k in ("job_id", "status", "progress", "stage")}
    if job["status"] == "done":
        payload["result"] = job["result"]
    if job["status"] == "failed":
        payload["error"] = job.get("error")
    return envelope(payload)


@app.get("/api/v1/jobs/{job_id}/events")
def job_events(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "job not found"})

    def stream():
        last = None
        for _ in range(600):
            payload = {"status": job["status"], "progress": job["progress"], "stage": job["stage"]}
            if payload != last:
                yield f"data: {json.dumps(payload)}\n\n"
                last = payload
            if job["status"] in ("done", "failed"):
                break
            time.sleep(0.25)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)}
    detail.setdefault("request_id", "req_" + uuid.uuid4().hex[:12])
    return JSONResponse({"error": detail}, status_code=exc.status_code)

# --------------------------------------------------------------------------
# static web app (spec 13): `npm run build` leaves plain files in frontend/out,
# which this process serves at "/" so there is one command and one port.
# --------------------------------------------------------------------------

_FRONTEND_OUT = config.BACKEND_DIR.parent / "frontend" / "out"
if _FRONTEND_OUT.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_FRONTEND_OUT), html=True), name="web")
