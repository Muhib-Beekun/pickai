# Facility Console

Map-centric setup, operations, slotting, and simulation for PickAI.

## Modes

| Mode | Features |
|------|----------|
| **Setup** | Locations inspector (hazmat, temp, weight, pick height), zones (pedestrian/forklift), docks, aisle rules + status, route policy, cart limits, labor standards, BYOK, pick history import |
| **Operations** | Pick + put + replen tasks, live aisle block/congestion toggle, replan, multi-picker, heat layers, route playback slider, slotting hints, labor estimate |
| **Slotting** | ABC velocity, SKU affinity heat, move suggestions with walk burden saved |
| **Simulation** | Sample-week what-if, ROI %, baseline vs draft distance/duration |
| **Scenario compare** | Quick picker/method comparison |

## Routing

| Policy | Engine |
|--------|--------|
| `shortest_path` | OR-Tools TSP (default) |
| `s_shape` | Classical S-shape aisle traversal |
| `largest_gap` | Largest-gap aisle heuristic |
| `combined` | Best of S-shape and return |
| `return_policy` | Return traversal per aisle |

## Picking methods

- **discrete** — one order per trip
- **batch** — multi-order until cart limits
- **wave** — all lines in one optimize pass
- **zone** — zone split across pickers

Cart splits on max lines, max weight (kg), and max pieces.

## Task interleaving

- `off` — separate pick / put / replen routes
- `same_zone` — merge tasks within zone
- `aggressive` — single interleaved route

## API

| Endpoint | Purpose |
|----------|---------|
| `GET/PUT /v1/facility/profile` | Profile CRUD |
| `PATCH /v1/facility/aisles/{id}?status=` | Live aisle open/blocked/congested |
| `POST /v1/facility/pick-history/import` | CSV pick history |
| `GET /v1/facility/slotting/suggestions` | ABC + affinity move list |
| `POST /v1/facility/simulate` | What-if ROI |
| `POST /v1/tasks/optimize` | Pick + put + replen |
| `POST /v1/tasks/optimize/async` | Background optimize + optional callback |
| `GET /v1/tasks/{run_id}/playback` | Route playback frames |
| `GET /v1/facility/profile/export?format=geojson` | WMS export |

## Samples

- `samples/pick_history_sample.csv` — slotting / ABC demo input

## Docker

```powershell
docker compose up -d --build
```

- Facility Console: http://localhost:8502
- API: http://localhost:8000/docs
