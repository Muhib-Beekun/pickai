# WMS Integration Guide

PickAI is a **pick-path optimization service** your WMS calls over REST. It does not replace inventory, order management, or picker mobile UI. You send released wave lines; PickAI returns an optimized travel sequence and metadata your WMS can apply to pick-task ordering.

## Who This Is For

This guide is for WMS admins and integration developers who need optimized pick sequences without writing Python code.

## 5-Minute Quick Start

1. Start services: `docker compose up`
2. Check API health: `GET http://localhost:8000/v1/health`
3. Send a wave to optimize: `POST /v1/waves/optimize`
4. Poll result: `GET /v1/runs/{run_id}`

## Authentication

- Header: `X-API-Key`
- Environment variable: `PICKAI_API_KEY`

## Primary Integration Flow (REST)

1. Export released wave lines from your WMS as JSON.
2. POST payload to `/v1/waves/optimize`.
3. Receive `run_id`.
4. Poll `/v1/runs/{run_id}` until status is `succeeded`.
5. Apply returned location sequence to your WMS pick-task ordering.

Persist these response fields if downstream workflows depend on operator state or reporting:

- `ladder_state_after`
- `processing_time_ms`
- `estimated_picker_time_saved_s`

### PowerShell Example

```powershell
$body = Get-Content samples/expected_optimize_request.json -Raw
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/waves/optimize" -Headers @{"X-API-Key"="dev"} -ContentType "application/json" -Body $body
```

### Curl Example

```bash
curl -X POST "http://localhost:8000/v1/waves/optimize" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev" \
  --data @samples/expected_optimize_request.json
```

## CSV Upload Fallback

Endpoint: `POST /v1/imports/csv`

Use `samples/order_lines_with_aisles.csv` to validate your mapping before pointing to live exports.

## Data Formats

PickAI normalized columns:

- `OrderNumber`
- `SKU`
- `PCS`
- `DATE`
- `x`
- `y`
- `aisle`
- `level`
- `Coord`

Mendeley mapping used by adapter:

- `Picking_Wave.order_id` -> `OrderNumber`
- `Picking_Wave.sku` -> `SKU`
- `Picking_Wave.quantity` -> `PCS`
- `Storage_Location.x` -> `x`
- `Storage_Location.y` -> `y`
- `Storage_Location.aisle` -> `aisle`
- `Storage_Location.level` -> `level`

Example generic WMS mappings (not vendor-certified):

- Manhattan: `order_nbr`, `item_id`, `pick_loc`, `qty`
- Blue Yonder: `order_id`, `sku_id`, `location_code`, `quantity`
- SAP EWM-style export: `DOCID`, `MATNR`, `LGPLA`, `ANFME`

## Equipment and Ladder Fields

Set these in `constraints`:

- `equipment_mode`: `walker` or `forklift`
- `ladder_must_stay_in_aisle`: true/false
- `start_position`: current picker or ladder position

Related response fields:

- `ladder_state_after`: last ladder position after the optimized route completes
- `processing_time_ms`: optimizer runtime for the request
- `estimated_picker_time_saved_s`: estimated time saved versus the naive baseline route

Reference schemas:

- `docs/openapi.json`
- `docs/tool-schema-compute_optimal_pick_path.json`

## Errors and Retries

- Include `idempotency_key` to prevent duplicate run creation on retries.
- Standard response envelopes include `request_id` for tracing.

## What PickAI Does Not Do

- No inventory synchronization.
- No writes into WMS master data.
- No wave release orchestration.

## Worked Example

Input: `data/fixtures/mendeley_sample.csv`

1. Convert rows to `OptimizeRequest` order lines.
2. Submit `/v1/waves/optimize`.
3. Read `sequence` in result as ordered travel legs and pick stops.
4. Persist `ladder_state_after` if the next wave should resume from the prior ladder location.
