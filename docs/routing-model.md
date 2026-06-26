# Routing Model (2.5D)

PickAI uses a hybrid deterministic routing model:

- 2D floor routing for `(x, y)` stop order optimization.
- 2.5D vertical pick cost at stop transitions using `level` / `z` fields.

## Concept diagram

```text
Depot/Start -> floor route over (x,y) graph -> stop i
                                         |-> pick cost(level/z change)
                                         |-> stop i+1
```

## Components

1. Tour solver:
- Default: OR-Tools TSP (`PICKAI_SOLVER=ortools`)
- Fallback: nearest-neighbor heuristic (`PICKAI_SOLVER=heuristic`)

2. Equipment model:
- Walker: lower speed, higher vertical handling cost
- Forklift: higher speed, one-way aisle penalties, no ladder relocate requirement

3. Ladder state:
- Input constraint: `start_position`
- Output state: `ladder_state_after`

4. Aisle policy:
- `ladder_must_stay_in_aisle=true` blocks cross-aisle routes.

5. Time-saved metric:
- Compare optimized route vs naive nearest-neighbor baseline on same wave.

## API fields produced

- `result.processing_time_ms`
- `result.estimated_picker_time_saved_s`
- `result.ladder_state_after`
