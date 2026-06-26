# API Contracts (v1)

This document summarizes the PickAI REST contracts.

## Response envelope

Successful responses:

```json
{
  "data": {},
  "meta": {
    "request_id": "req_xxx",
    "version": "v1"
  }
}
```

Errors follow FastAPI HTTP status codes with a typed `detail` message.

## Endpoints

- `GET /v1/health`
- `POST /v1/waves/optimize`
- `GET /v1/runs/{run_id}`
- `POST /v1/imports/csv`
- `POST /v1/webhooks/wms`

## Optimize request

Core fields:

- `order_lines[]` with `order_id`, `line_id`, `sku`, `location_id`, `quantity`, `x`, `y`
- `constraints` with `equipment_mode`, `ladder_must_stay_in_aisle`, optional `start_position`
- `idempotency_key` recommended for safe retries

## Optimize response

- `data.run_id`
- `data.status`
- `data.result` when completed, including route sequence and totals

## Full OpenAPI

The generated OpenAPI schema is in `docs/openapi.json`.

## Tool Calling

For hybrid LLM + solver integrations, use the published tool schema:

- `docs/tool-schema-compute_optimal_pick_path.json`

The LLM should only produce validated parameters and then call `compute_optimal_pick_path`; the deterministic solver computes all route distances and order.
