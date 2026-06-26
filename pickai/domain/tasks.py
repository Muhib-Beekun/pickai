from __future__ import annotations

import time

from pickai.contracts import EquipmentMode, LadderState, OptimizeConstraints
from pickai.contracts.facility import (
    FacilityProfile,
    ResourcePool,
    TaskLine,
    TaskOptimizeRequest,
    TaskOptimizeResult,
    ResourceAssignment,
)
from pickai.contracts.types import OrderLine
from pickai.domain.heat import build_heat_maps
from pickai.domain.multi_resource import optimize_multi_resource
from pickai.facility.store import facility_store


def _to_order_line(task: TaskLine) -> OrderLine:
    return OrderLine(
        order_id=task.order_id,
        line_id=task.line_id,
        sku=task.sku,
        location_id=task.location_id,
        quantity=task.quantity,
        x=task.x,
        y=task.y,
        z=task.z,
        level=task.level,
    )


def _parse_constraints(raw: dict | None) -> OptimizeConstraints:
    if not raw:
        return OptimizeConstraints()
    start_raw = raw.get("start_position")
    start = LadderState(**start_raw) if start_raw else None
    return OptimizeConstraints(
        equipment_mode=EquipmentMode(raw.get("equipment_mode", "walker")),
        ladder_must_stay_in_aisle=bool(raw.get("ladder_must_stay_in_aisle", False)),
        start_position=start,
    )


def _apply_blocked_filter(profile: FacilityProfile, lines: list[OrderLine]) -> tuple[list[OrderLine], list[str]]:
    blocked_ids = {loc.location_id for loc in profile.locations if loc.blocked}
    blocked_aisles = {a.aisle_id for a in profile.aisles if a.blocked}
    kept: list[OrderLine] = []
    warnings: list[str] = []
    for line in lines:
        aisle = f"A{int(line.x) + 1}"
        if line.location_id in blocked_ids or aisle in blocked_aisles:
            warnings.append(f"Skipped blocked location {line.location_id}")
            continue
        kept.append(line)
    return kept, warnings


def _cart_split(lines: list[OrderLine], max_lines: int) -> list[list[OrderLine]]:
    if len(lines) <= max_lines:
        return [lines]
    return [lines[i : i + max_lines] for i in range(0, len(lines), max_lines)]


def optimize_tasks(
    request: TaskOptimizeRequest,
    profile: FacilityProfile | None = None,
) -> TaskOptimizeResult:
    start = time.perf_counter()
    profile = profile or facility_store.load()
    constraints = _parse_constraints(request.constraints)

    pick_tasks = [_to_order_line(t) for t in request.tasks if t.task_type == "pick"]
    put_tasks = [_to_order_line(t) for t in request.tasks if t.task_type == "put"]

    pick_tasks, pick_block_warnings = _apply_blocked_filter(profile, pick_tasks)
    put_tasks, put_block_warnings = _apply_blocked_filter(profile, put_tasks)

    resources = request.resources or profile.resources
    run_id = request.idempotency_key or "task-run"

    assignments: list[ResourceAssignment] = []
    all_warnings = pick_block_warnings + put_block_warnings
    total_distance = 0.0
    total_duration = 0.0

    pick_batches = _cart_split(pick_tasks, profile.cart_max_lines)
    picker_idx = 0
    for batch in pick_batches:
        picker_assignments, warnings = optimize_multi_resource(
            profile,
            batch,
            constraints,
            ResourcePool(pickers=1, putters=resources.putters),
            f"{run_id}-pick-batch-{picker_idx}",
            resource_type="picker",
        )
        all_warnings.extend(warnings)
        for item in picker_assignments:
            result = item["result"]
            total_distance += float(result.get("total_distance_m", 0))
            total_duration += float(result.get("total_duration_s", 0))
            assignments.append(
                ResourceAssignment(
                    resource_id=item["resource_id"],
                    resource_type=item["resource_type"],
                    zone_id=item.get("zone_id"),
                    order_lines=item.get("order_lines", []),
                    result=result,
                    conflict_warnings=warnings,
                )
            )
        picker_idx += 1

    if put_tasks and profile.task_interleaving != "off":
        put_assignments, warnings = optimize_multi_resource(
            profile,
            put_tasks,
            constraints,
            resources,
            f"{run_id}-put",
            resource_type="putter",
        )
        all_warnings.extend(warnings)
        for item in put_assignments:
            result = item["result"]
            total_distance += float(result.get("total_distance_m", 0))
            total_duration += float(result.get("total_duration_s", 0))
            assignments.append(
                ResourceAssignment(
                    resource_id=item["resource_id"],
                    resource_type=item["resource_type"],
                    zone_id=item.get("zone_id"),
                    order_lines=item.get("order_lines", []),
                    result=result,
                    conflict_warnings=warnings,
                )
            )

    assignment_dicts = [
        {**a.model_dump(), "lines": [{"x": t.x, "y": t.y, "aisle": f"A{int(t.x) + 1}"} for t in pick_tasks + put_tasks]}
        for a in assignments
    ]
    heat_maps = build_heat_maps(profile, pick_tasks + put_tasks, assignment_dicts)

    naive_multiplier = max(1, len(pick_tasks) + len(put_tasks))
    empty_travel_pct = 0.0
    if total_distance > 0 and naive_multiplier > 0:
        empty_travel_pct = max(0.0, min(100.0, (1.0 - (len(assignments) / naive_multiplier)) * 100.0))

    processing_ms = int((time.perf_counter() - start) * 1000)
    return TaskOptimizeResult(
        run_id=run_id,
        assignments=assignments,
        heat_maps=heat_maps,
        total_distance_m=total_distance,
        total_duration_s=total_duration,
        processing_time_ms=processing_ms,
        empty_travel_pct=empty_travel_pct,
        conflict_warnings=list(dict.fromkeys(all_warnings)),
    )
