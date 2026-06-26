from __future__ import annotations

from pickai.contracts import OptimizeRequest, OptimizedWave, RouteSegment

from .equipment import PROFILES, forklift_direction_penalty, infer_aisle_id, load_aisle_rules
from .routing import create_picking_route, distance_picking


def _start_point(request: OptimizeRequest, y_low: float) -> list[float]:
    if request.constraints.start_position is not None:
        return [request.constraints.start_position.x, request.constraints.start_position.y]
    if request.constraints.depot is not None:
        return [request.constraints.depot.x, request.constraints.depot.y]
    return [0, y_low]


def optimize_wave(request: OptimizeRequest) -> OptimizedWave:
    y_low = 5.5
    y_high = 50.0
    wave_id = request.idempotency_key or "wave-1"

    origin = _start_point(request, y_low)
    unique_points = sorted({(line.x, line.y) for line in request.order_lines})
    list_locs = [list(point) for point in unique_points]

    route_distance, path = create_picking_route(origin, list_locs, y_low, y_high)
    profile = PROFILES[request.constraints.equipment_mode.value]
    one_way_rules = load_aisle_rules()

    sequence: list[RouteSegment] = []
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

        sequence.append(
            RouteSegment(
                **{
                    "from": f"({prev_point[0]}, {prev_point[1]})",
                    "to": f"({next_point[0]}, {next_point[1]})",
                },
                segment_type="walk",
                distance_m=segment_distance,
                duration_s=segment_duration,
            )
        )
        sequence.append(
            RouteSegment(
                **{
                    "from": f"({next_point[0]}, {next_point[1]})",
                    "to": f"({next_point[0]}, {next_point[1]})",
                },
                segment_type="pick",
                distance_m=0.0,
                duration_s=1.0,
            )
        )

    total_duration = sum(segment.duration_s for segment in sequence)
    total_distance = float(route_distance) + sum(
        seg.distance_m for seg in sequence if seg.segment_type == "ladder_relocate"
    )

    return OptimizedWave(
        wave_id=wave_id,
        sequence=sequence,
        total_distance_m=total_distance,
        total_duration_s=float(total_duration),
        picks=request.order_lines,
    )
