from __future__ import annotations

from pickai.contracts import OptimizeRequest, OptimizedWave, RouteSegment

from .routing import create_picking_route, distance_picking


EQUIPMENT_SPEED_MPS = {
    "walker": 1.4,
    "forklift": 2.5,
}


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
    speed = EQUIPMENT_SPEED_MPS[request.constraints.equipment_mode.value]

    sequence: list[RouteSegment] = []
    for idx in range(1, len(path)):
        prev_point = path[idx - 1]
        next_point = path[idx]
        segment_distance = float(distance_picking(prev_point, next_point, y_low, y_high))
        sequence.append(
            RouteSegment(
                **{
                    "from": f"({prev_point[0]}, {prev_point[1]})",
                    "to": f"({next_point[0]}, {next_point[1]})",
                },
                segment_type="walk",
                distance_m=segment_distance,
                duration_s=segment_distance / speed if speed > 0 else 0.0,
            )
        )

    total_duration = sum(segment.duration_s for segment in sequence)

    return OptimizedWave(
        wave_id=wave_id,
        sequence=sequence,
        total_distance_m=float(route_distance),
        total_duration_s=float(total_duration),
        picks=request.order_lines,
    )
