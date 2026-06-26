from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from fastapi import FastAPI, File, Header, HTTPException, Query, UploadFile

from pickai.contracts import (
    OptimizeRequest,
    OptimizeResponse,
    OptimizeResponseData,
    ResponseMeta,
    RunStatus,
    WmsWebhookPayload,
)
from pickai.domain.optimizer import optimize_wave


app = FastAPI(title="PickAI API", version="v1")

RUN_STORE: dict[str, RunStatus] = {}


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
        meta=ResponseMeta(request_id=f"req_{uuid.uuid4().hex[:12]}", version="v1"),
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
