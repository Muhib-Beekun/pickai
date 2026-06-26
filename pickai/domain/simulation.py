from __future__ import annotations

import random

from pickai.contracts.facility import FacilityProfile, SimulationResult, TaskLine, TaskOptimizeRequest
from pickai.contracts.types import OrderLine
from pickai.domain.slotting import pick_history_store
from pickai.domain.tasks import optimize_tasks


def _records_to_tasks(records: list, sample_size: int) -> list[TaskLine]:
    sample = records[:sample_size] if len(records) >= sample_size else records
    return [
        TaskLine(
            task_type="pick",
            order_id=r.order_id,
            line_id=f"{r.order_id}-{r.sku}",
            sku=r.sku,
            location_id=r.location_id,
            quantity=r.quantity,
            x=r.x,
            y=r.y,
        )
        for r in sample
    ]


def run_simulation(
    baseline: FacilityProfile,
    draft: FacilityProfile,
    sample_size: int = 100,
    seed: int = 42,
) -> SimulationResult:
    records = pick_history_store.load(baseline.tenant_id, baseline.facility_id)
    if not records:
        rng = random.Random(seed)
        tasks = []
        for idx, loc in enumerate(baseline.locations[:sample_size]):
            tasks.append(
                TaskLine(
                    task_type="pick",
                    order_id=f"sim-{idx // 5}",
                    line_id=str(idx),
                    sku=f"SKU-{idx % 20}",
                    location_id=loc.location_id,
                    quantity=1,
                    x=loc.x,
                    y=loc.y,
                    level=loc.level,
                )
            )
    else:
        tasks = _records_to_tasks(records, sample_size)

    base_req = TaskOptimizeRequest(tasks=tasks, idempotency_key="sim-baseline")
    draft_req = TaskOptimizeRequest(tasks=tasks, idempotency_key="sim-draft")

    base_result = optimize_tasks(base_req, profile=baseline)
    draft_result = optimize_tasks(draft_req, profile=draft)

    distance_saved = base_result.total_distance_m - draft_result.total_distance_m
    duration_saved = base_result.total_duration_s - draft_result.total_duration_s
    roi_pct = 0.0
    if base_result.total_distance_m > 0:
        roi_pct = (distance_saved / base_result.total_distance_m) * 100.0

    return SimulationResult(
        sample_size=len(tasks),
        baseline_distance_m=base_result.total_distance_m,
        draft_distance_m=draft_result.total_distance_m,
        distance_saved_m=distance_saved,
        baseline_duration_s=base_result.total_duration_s,
        draft_duration_s=draft_result.total_duration_s,
        duration_saved_s=duration_saved,
        roi_pct=round(roi_pct, 2),
        baseline_conflicts=len(base_result.conflict_warnings),
        draft_conflicts=len(draft_result.conflict_warnings),
    )
