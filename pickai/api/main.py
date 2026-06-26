from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from fastapi import BackgroundTasks, FastAPI, File, Header, HTTPException, Query, UploadFile

from pickai.contracts import (
    OptimizeRequest,
    OptimizeResponse,
    OptimizeResponseData,
    ResponseMeta,
    RunStatus,
    WmsWebhookPayload,
)
from pickai.contracts.facility import (
    AisleRule,
    AisleStatus,
    FacilityProfile,
    SimulationResult,
    TaskOptimizeRequest,
)
from pickai.domain.optimizer import optimize_wave
from pickai.domain.simulation import run_simulation
from pickai.domain.slotting import generate_slotting_suggestions, pick_history_store
from pickai.domain.tasks import optimize_tasks
from pickai.facility.store import facility_store


app = FastAPI(title="PickAI API", version="v1")

RUN_STORE: dict[str, RunStatus] = {}
TASK_STORE: dict[str, dict] = {}
WEBHOOK_CALLBACKS: dict[str, str] = {}


def _validate_api_key(api_key: str | None) -> None:
    expected = "dev"
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/v1/health")
def health() -> dict:
    return {
        "data": {"status": "ok", "timestamp": datetime.utcnow().isoformat()},
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.post("/v1/waves/optimize", response_model=OptimizeResponse)
def optimize(request: OptimizeRequest, x_api_key: str | None = Header(default=None)) -> OptimizeResponse:
    _validate_api_key(x_api_key)

    run_id = request.idempotency_key or f"run_{uuid.uuid4().hex[:12]}"
    RUN_STORE[run_id] = RunStatus(run_id=run_id, status="running", phase="optimize", progress=10)
    try:
        result = optimize_wave(request)
        status = RunStatus(run_id=run_id, status="succeeded", phase="complete", progress=100, result=result)
        RUN_STORE[run_id] = status
    except Exception as exc:
        RUN_STORE[run_id] = RunStatus(
            run_id=run_id,
            status="failed",
            phase="optimize",
            progress=100,
            error=str(exc),
        )

    run = RUN_STORE[run_id]
    return OptimizeResponse(
        data=OptimizeResponseData(run_id=run_id, status=run.status, result=run.result),
        meta=ResponseMeta(
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            version="v1",
            processing_time_ms=run.result.processing_time_ms if run.result else None,
            estimated_picker_time_saved_s=run.result.estimated_picker_time_saved_s if run.result else None,
        ),
    )


@app.get("/v1/runs/{run_id}")
def get_run(run_id: str, x_api_key: str | None = Header(default=None)) -> dict:
    _validate_api_key(x_api_key)
    if run_id not in RUN_STORE:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {
        "data": RUN_STORE[run_id].model_dump(by_alias=True),
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.post("/v1/imports/csv")
async def import_csv(
    file: UploadFile = File(...),
    order_col: str = Query(default="OrderNumber"),
    sku_col: str = Query(default="SKU"),
    qty_col: str = Query(default="PCS"),
    x_col: str = Query(default="x"),
    y_col: str = Query(default="y"),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    content = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    lines = []
    for idx, row in enumerate(reader):
        lines.append(
            {
                "order_id": str(row.get(order_col, f"order-{idx}")),
                "line_id": str(idx + 1),
                "sku": str(row.get(sku_col, "UNKNOWN")),
                "location_id": f"loc-{idx + 1}",
                "quantity": int(float(row.get(qty_col, 1))),
                "x": float(row.get(x_col, 0.0)),
                "y": float(row.get(y_col, 0.0)),
            }
        )

    return {
        "data": {"count": len(lines), "order_lines": lines},
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.post("/v1/webhooks/wms")
def wms_webhook(
    payload: WmsWebhookPayload,
    x_signature: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    signature_status = "present" if x_signature else "missing"
    return {
        "data": {
            "accepted": True,
            "event": payload.event,
            "signature_validation": f"stub_{signature_status}",
        },
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.get("/v1/facility/profile")
def get_facility_profile(
    tenant_id: str = Query(default="default"),
    facility_id: str = Query(default="main"),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    profile = facility_store.load(tenant_id=tenant_id, facility_id=facility_id)
    return {
        "data": profile.model_dump(mode="json"),
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.put("/v1/facility/profile")
def put_facility_profile(
    profile: FacilityProfile,
    publish: bool = Query(default=False),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    saved = facility_store.publish(profile) if publish else facility_store.save(profile)
    return {
        "data": saved.model_dump(mode="json"),
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.get("/v1/facility/profile/export")
def export_facility_profile(
    tenant_id: str = Query(default="default"),
    facility_id: str = Query(default="main"),
    format: str = Query(default="json"),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    profile = facility_store.load(tenant_id=tenant_id, facility_id=facility_id)
    if format == "geojson":
        return {
            "data": facility_store.export_geojson(profile),
            "meta": {
                "request_id": f"req_{uuid.uuid4().hex[:12]}",
                "version": "v1",
                "facility_profile_version": profile.version,
            },
        }
    return {
        "data": profile.model_dump(mode="json"),
        "meta": {
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
            "version": "v1",
            "facility_profile_version": profile.version,
        },
    }


@app.post("/v1/tasks/optimize")
def optimize_tasks_endpoint(
    request: TaskOptimizeRequest,
    tenant_id: str = Query(default="default"),
    facility_id: str = Query(default="main"),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    profile = facility_store.load(tenant_id=tenant_id, facility_id=facility_id)
    if request.facility_profile_version and request.facility_profile_version != profile.version:
        raise HTTPException(
            status_code=409,
            detail=f"facility_profile_version_mismatch: expected {profile.version}",
        )
    result = optimize_tasks(request, profile=profile)
    return {
        "data": result.model_dump(mode="json"),
        "meta": {
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
            "version": "v1",
            "processing_time_ms": result.processing_time_ms,
            "facility_profile_version": profile.version,
        },
    }


def _run_async_optimize(run_id: str, request: TaskOptimizeRequest, profile: FacilityProfile, callback_url: str | None) -> None:
    TASK_STORE[run_id] = {"status": "running", "progress": 10}
    try:
        result = optimize_tasks(request, profile=profile)
        TASK_STORE[run_id] = {"status": "succeeded", "progress": 100, "result": result.model_dump(mode="json")}
        if callback_url:
            import httpx

            try:
                httpx.post(callback_url, json={"run_id": run_id, "status": "succeeded"}, timeout=10)
            except Exception:
                pass
    except Exception as exc:
        TASK_STORE[run_id] = {"status": "failed", "progress": 100, "error": str(exc)}


@app.post("/v1/tasks/optimize/async")
def optimize_tasks_async(
    request: TaskOptimizeRequest,
    background_tasks: BackgroundTasks,
    callback_url: str | None = Query(default=None),
    tenant_id: str = Query(default="default"),
    facility_id: str = Query(default="main"),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    profile = facility_store.load(tenant_id=tenant_id, facility_id=facility_id)
    run_id = request.idempotency_key or f"task_{uuid.uuid4().hex[:12]}"
    if callback_url:
        WEBHOOK_CALLBACKS[run_id] = callback_url
    background_tasks.add_task(_run_async_optimize, run_id, request, profile, callback_url)
    return {
        "data": {"run_id": run_id, "status": "accepted"},
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.get("/v1/tasks/{run_id}")
def get_task_run(run_id: str, x_api_key: str | None = Header(default=None)) -> dict:
    _validate_api_key(x_api_key)
    if run_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail="task_run_not_found")
    return {
        "data": TASK_STORE[run_id],
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.get("/v1/tasks/{run_id}/playback")
def get_task_playback(run_id: str, x_api_key: str | None = Header(default=None)) -> dict:
    _validate_api_key(x_api_key)
    if run_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail="task_run_not_found")
    result = TASK_STORE[run_id].get("result", {})
    return {
        "data": {"frames": result.get("route_playback", [])},
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.patch("/v1/facility/aisles/{aisle_id}")
def patch_aisle_status(
    aisle_id: str,
    status: str = Query(...),
    tenant_id: str = Query(default="default"),
    facility_id: str = Query(default="main"),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    profile = facility_store.load(tenant_id=tenant_id, facility_id=facility_id)
    try:
        new_status = AisleStatus(status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_aisle_status") from exc

    updated = False
    for aisle in profile.aisles:
        if aisle.aisle_id == aisle_id:
            aisle.status = new_status
            aisle.blocked = new_status == AisleStatus.blocked
            updated = True
    if not updated:
        profile.aisles.append(AisleRule(aisle_id=aisle_id, status=new_status, blocked=new_status == AisleStatus.blocked))
    saved = facility_store.save(profile)
    return {"data": saved.model_dump(mode="json"), "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"}}


@app.post("/v1/facility/pick-history/import")
async def import_pick_history(
    file: UploadFile = File(...),
    tenant_id: str = Query(default="default"),
    facility_id: str = Query(default="main"),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    content = (await file.read()).decode("utf-8")
    count = pick_history_store.import_csv(tenant_id, facility_id, content)
    return {
        "data": {"imported": count},
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }


@app.get("/v1/facility/slotting/suggestions")
def slotting_suggestions(
    tenant_id: str = Query(default="default"),
    facility_id: str = Query(default="main"),
    top_n: int = Query(default=10, ge=1, le=50),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    profile = facility_store.load(tenant_id=tenant_id, facility_id=facility_id)
    history = pick_history_store.load(tenant_id, facility_id)
    suggestions = generate_slotting_suggestions(profile, history, top_n=top_n)
    return {
        "data": [s.model_dump(mode="json") for s in suggestions],
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1", "history_rows": len(history)},
    }


@app.post("/v1/facility/simulate")
def simulate_facility(
    draft: FacilityProfile,
    sample_size: int = Query(default=100, ge=10, le=500),
    tenant_id: str = Query(default="default"),
    facility_id: str = Query(default="main"),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _validate_api_key(x_api_key)
    baseline = facility_store.load(tenant_id=tenant_id, facility_id=facility_id)
    result: SimulationResult = run_simulation(baseline, draft, sample_size=sample_size)
    return {
        "data": result.model_dump(mode="json"),
        "meta": {"request_id": f"req_{uuid.uuid4().hex[:12]}", "version": "v1"},
    }
