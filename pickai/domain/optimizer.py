from __future__ import annotations

import os
import time

from pickai.contracts import OptimizeRequest, OptimizedWave, RouteSegment

from .equipment import PROFILES, forklift_direction_penalty, infer_aisle_id, load_aisle_rules
from .routing import create_picking_route, distance_picking
from .solver_ortools import solve_pick_path_tsp


def _start_point(request: OptimizeRequest, y_low: float) -> list[float]:
    if request.constraints.start_position is not None:
        return [request.constraints.start_position.x, request.constraints.start_position.y]
    if request.constraints.depot is not None:
        return [request.constraints.depot.x, request.constraints.depot.y]
    return [0, y_low]


def _naive_route_distance(origin: list[float], list_locs: list[list[float]], y_low: float, y_high: float) -> float:
    remaining = [list(item) for item in list_locs]
    start_loc = list(origin)
    distance_total = 0.0
    while remaining:
        next_loc = min(remaining, key=lambda loc: distance_picking(start_loc, loc, y_low, y_high))
        distance_total += distance_picking(start_loc, next_loc, y_low, y_high)
        start_loc = next_loc
        remaining.remove(next_loc)
    distance_total += distance_picking(start_loc, origin, y_low, y_high)
    return float(distance_total)


def _build_route_with_solver(origin: list[float], list_locs: list[list[float]], y_low: float, y_high: float) -> tuple[float, list[list[float]]]:
    solver_mode = os.getenv("PICKAI_SOLVER", "ortools").strip().lower()
    if solver_mode == "heuristic":
        return create_picking_route(origin, list_locs, y_low, y_high)

    try:
        ordered = solve_pick_path_tsp(
            locations=[(loc[0], loc[1]) for loc in list_locs],
            depot=(origin[0], origin[1]),
            distance_fn=lambda a, b: float(distance_picking([a[0], a[1]], [b[0], b[1]], y_low, y_high)),
        )
        path = [list(origin)] + [[float(x), float(y)] for x, y in ordered] + [list(origin)]
        total = 0.0
        for idx in range(1, len(path)):
            total += distance_picking(path[idx - 1], path[idx], y_low, y_high)
        return float(total), path
    except Exception:
        return create_picking_route(origin, list_locs, y_low, y_high)


def optimize_wave(request: OptimizeRequest) -> OptimizedWave:
    start_time = time.perf_counter()
    y_low = 5.5
    y_high = 50.0
    wave_id = request.idempotency_key or "wave-1"

    origin = _start_point(request, y_low)
    unique_points = sorted({(line.x, line.y) for line in request.order_lines})
    list_locs = [list(point) for point in unique_points]

    route_distance, path = _build_route_with_solver(origin, list_locs, y_low, y_high)
    naive_distance = _naive_route_distance(origin, list_locs, y_low, y_high)
    profile = PROFILES[request.constraints.equipment_mode.value]
    one_way_rules = load_aisle_rules()

    sequence: list[RouteSegment] = []
    last_level: str | None = request.constraints.start_position.level if request.constraints.start_position else None
    for idx in range(1, len(path)):
        prev_point = path[idx - 1]
        next_point = path[idx]
        prev_aisle = infer_aisle_id(prev_point)
        next_aisle = infer_aisle_id(next_point)

        if prev_aisle != next_aisle:
            if request.constraints.ladder_must_stay_in_aisle:
                raise ValueError(
                    f"ladder_must_stay_in_aisle is enabled but route crosses {prev_aisle} -> {next_aisle}"
                )
            sequence.append(
                RouteSegment(
                    **{"from": prev_aisle, "to": next_aisle},
                    segment_type="ladder_relocate",
                    distance_m=profile.relocate_penalty_distance_m,
                    duration_s=profile.relocate_penalty_s,
                )
            )

        segment_distance = float(distance_picking(prev_point, next_point, y_low, y_high))
        segment_duration = (segment_distance / profile.speed_mps) + profile.turn_penalty_s
        if request.constraints.equipment_mode.value == "forklift":
            segment_duration += forklift_direction_penalty(prev_point, next_point, one_way_rules)

        walk_segment = RouteSegment(
            **{
                "from": f"({prev_point[0]}, {prev_point[1]})",
                "to": f"({next_point[0]}, {next_point[1]})",
            },
            segment_type="walk",
            distance_m=segment_distance,
            duration_s=segment_duration,
        )
        sequence.append(walk_segment)

        matched_line = next(
            (line for line in request.order_lines if float(line.x) == float(next_point[0]) and float(line.y) == float(next_point[1])),
            None,
        )
        pick_duration_s = 1.0
        if matched_line and matched_line.level is not None and last_level is not None and matched_line.level != last_level:
            pick_duration_s += profile.vertical_pick_s
        if matched_line and matched_line.level is not None:
            last_level = matched_line.level

        sequence.append(
            RouteSegment(
                **{
                    "to": f"({next_point[0]}, {next_point[1]})",
                    "from": f"({next_point[0]}, {next_point[1]})",
                },
                segment_type="pick",
                distance_m=0.0,
                duration_s=pick_duration_s,
            )
        )

    total_duration = sum(segment.duration_s for segment in sequence)
    total_distance = float(route_distance) + sum(
        seg.distance_m for seg in sequence if seg.segment_type == "ladder_relocate"
    )
    processing_time_ms = int((time.perf_counter() - start_time) * 1000)
    estimated_picker_time_saved_s = max(0.0, (naive_distance - float(route_distance)) / max(profile.speed_mps, 0.1))

    ladder_state_after = request.constraints.start_position
    if len(path) > 1:
        end_point = path[-2]
        ladder_state_after = request.constraints.start_position.model_copy() if request.constraints.start_position else None
        if ladder_state_after is None:
            from pickai.contracts import LadderState

            ladder_state_after = LadderState(aisle=infer_aisle_id(end_point), level=last_level, x=end_point[0], y=end_point[1])
        else:
            ladder_state_after.aisle = infer_aisle_id(end_point)
            ladder_state_after.level = last_level
            ladder_state_after.x = end_point[0]
            ladder_state_after.y = end_point[1]

    return OptimizedWave(
        wave_id=wave_id,
        sequence=sequence,
        total_distance_m=total_distance,
        total_duration_s=float(total_duration),
        processing_time_ms=processing_time_ms,
        estimated_picker_time_saved_s=estimated_picker_time_saved_s,
        ladder_state_after=ladder_state_after,
        picks=request.order_lines,
    )
