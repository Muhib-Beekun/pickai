from __future__ import annotations

import time

from pickai.contracts import EquipmentMode, LadderState, OptimizeConstraints
from pickai.contracts.facility import (
    FacilityProfile,
    ResourceAssignment,
    TaskLine,
    TaskOptimizeRequest,
    TaskOptimizeResult,
)
from pickai.contracts.types import OrderLine
from pickai.domain.cart_splits import split_cart_capacity
from pickai.domain.heat import build_heat_maps
from pickai.domain.interleaving import interleave_tasks
from pickai.domain.labor import estimate_labor_s
from pickai.domain.multi_resource import optimize_multi_resource
from pickai.domain.picking_methods import split_by_picking_method
from pickai.domain.route_playback import build_route_playback
from pickai.domain.slotting import generate_slotting_suggestions, pick_history_store
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
        weight_kg=task.weight_kg,
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


def _aisle_blocked(profile: FacilityProfile, line: OrderLine) -> bool:
    aisle_id = next(
        (loc.aisle for loc in profile.locations if loc.location_id == line.location_id),
        f"A{int(line.x) + 1}",
    )
    for rule in profile.aisles:
        if rule.aisle_id == aisle_id and (rule.blocked or rule.status.value == "blocked"):
            return True
    return False


def _apply_blocked_filter(profile: FacilityProfile, lines: list[OrderLine]) -> tuple[list[OrderLine], list[str]]:
    blocked_ids = {loc.location_id for loc in profile.locations if loc.blocked}
    kept: list[OrderLine] = []
    warnings: list[str] = []
    for line in lines:
        if line.location_id in blocked_ids or _aisle_blocked(profile, line):
            warnings.append(f"Skipped blocked location/aisle for {line.location_id}")
            continue
        kept.append(line)
    return kept, warnings


def _check_equipment_zones(profile: FacilityProfile, lines: list[OrderLine], equipment: str) -> list[str]:
    warnings: list[str] = []
    for line in lines:
        for zone in profile.zones:
            if zone.x_min <= line.x <= zone.x_max:
                if equipment == "forklift" and zone.pedestrian_only:
                    warnings.append(f"Forklift requested in pedestrian-only zone {zone.zone_id}")
                if equipment == "walker" and zone.forklift_only:
                    warnings.append(f"Walker in forklift-only zone {zone.zone_id}")
    return warnings


def _assignments_from_items(items: list[dict], warnings: list[str]) -> list[ResourceAssignment]:
    out: list[ResourceAssignment] = []
    for item in items:
        out.append(
            ResourceAssignment(
                resource_id=item["resource_id"],
                resource_type=item["resource_type"],
                zone_id=item.get("zone_id"),
                order_lines=item.get("order_lines", []),
                result=item.get("result"),
                conflict_warnings=warnings,
            )
        )
    return out


def optimize_tasks(
    request: TaskOptimizeRequest,
    profile: FacilityProfile | None = None,
) -> TaskOptimizeResult:
    start = time.perf_counter()
    profile = profile or facility_store.load()
    constraints = _parse_constraints(request.constraints)

    pick_tasks = [_to_order_line(t) for t in request.tasks if t.task_type == "pick"]
    put_tasks = [_to_order_line(t) for t in request.tasks if t.task_type == "put"]
    replen_tasks = [_to_order_line(t) for t in request.tasks if t.task_type == "replen"]

    pick_tasks, w1 = _apply_blocked_filter(profile, pick_tasks)
    put_tasks, w2 = _apply_blocked_filter(profile, put_tasks)
    replen_tasks, w3 = _apply_blocked_filter(profile, replen_tasks)
    all_warnings = w1 + w2 + w3 + _check_equipment_zones(profile, pick_tasks + put_tasks, constraints.equipment_mode.value)

    resources = request.resources or profile.resources
    run_id = request.idempotency_key or "task-run"
    weight_map = {t.line_id: float(t.weight_kg or 1.0) for t in request.tasks}

    assignments: list[ResourceAssignment] = []
    total_distance = 0.0
    total_duration = 0.0
    all_playback = []

    if profile.picking_method.value == "zone":
        items, warnings = optimize_multi_resource(profile, pick_tasks, constraints, resources, f"{run_id}-zone", "picker")
        all_warnings.extend(warnings)
        assignments.extend(_assignments_from_items(items, warnings))
        for item in items:
            result = item["result"]
            total_distance += float(result.get("total_distance_m", 0))
            total_duration += float(result.get("total_duration_s", 0))
            all_playback.extend(build_route_playback(result))
        if put_tasks or replen_tasks:
            extra, w = interleave_tasks(profile, [], put_tasks, replen_tasks, constraints, f"{run_id}-put", weight_map)
            all_warnings.extend(w)
            assignments.extend(_assignments_from_items(extra, w))
            for item in extra:
                result = item["result"]
                total_distance += float(result.get("total_distance_m", 0))
                total_duration += float(result.get("total_duration_s", 0))
                all_playback.extend(build_route_playback(result))
    else:
        method_batches = split_by_picking_method(profile, pick_tasks, weight_map)
        for bidx, method_batch in enumerate(method_batches):
            cart_batches = split_cart_capacity(
                method_batch,
                profile.cart_max_lines,
                profile.cart_max_weight_kg,
                profile.cart_max_pieces,
                weight_map,
            )
            for cidx, cart_batch in enumerate(cart_batches):
                include_put = bidx == 0 and cidx == 0
                items, warnings = interleave_tasks(
                    profile,
                    cart_batch,
                    put_tasks if include_put else [],
                    replen_tasks if include_put else [],
                    constraints,
                    f"{run_id}-{bidx}-{cidx}",
                    weight_map,
                )
                all_warnings.extend(warnings)
                assignments.extend(_assignments_from_items(items, warnings))
                for item in items:
                    result = item["result"]
                    total_distance += float(result.get("total_distance_m", 0))
                    total_duration += float(result.get("total_duration_s", 0))
                    all_playback.extend(build_route_playback(result))

    loc_by_id = {loc.location_id: loc for loc in profile.locations}
    labor_s = estimate_labor_s(
        profile,
        len(pick_tasks) + len(put_tasks) + len(replen_tasks),
        total_duration,
        loc_by_id,
        pick_tasks + put_tasks + replen_tasks,
    )

    assignment_dicts = [
        {
            **a.model_dump(),
            "lines": [{"x": t.x, "y": t.y, "aisle": f"A{int(t.x) + 1}"} for t in pick_tasks + put_tasks + replen_tasks],
        }
        for a in assignments
    ]
    history = pick_history_store.load(profile.tenant_id, profile.facility_id)
    heat_maps = build_heat_maps(profile, pick_tasks + put_tasks + replen_tasks, assignment_dicts, history)
    slotting = generate_slotting_suggestions(profile, history)

    task_count = max(1, len(pick_tasks) + len(put_tasks) + len(replen_tasks))
    empty_travel_pct = max(0.0, min(100.0, (1.0 - len(assignments) / task_count) * 100.0))
    walk_distance = sum(
        float(seg.get("distance_m", 0))
        for a in assignments
        for seg in (a.result or {}).get("sequence", [])
        if seg.get("segment_type") == "walk"
    )
    deadhead_travel_pct = 0.0
    if total_distance > 0:
        deadhead_travel_pct = max(0.0, min(100.0, ((total_distance - walk_distance) / total_distance) * 100.0))

    return TaskOptimizeResult(
        run_id=run_id,
        assignments=assignments,
        heat_maps=heat_maps,
        slotting_suggestions=slotting,
        route_playback=all_playback,
        total_distance_m=total_distance,
        total_duration_s=total_duration,
        labor_estimate_s=labor_s,
        processing_time_ms=int((time.perf_counter() - start) * 1000),
        empty_travel_pct=empty_travel_pct,
        deadhead_travel_pct=deadhead_travel_pct,
        conflict_warnings=list(dict.fromkeys(all_warnings)),
    )
