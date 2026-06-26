from __future__ import annotations

from ast import literal_eval


def distance_picking(loc1: list[float], loc2: list[float], y_low: float, y_high: float) -> int:
    """Calculate shortest aisle-respecting walking distance between two points."""
    x1, y1 = loc1[0], loc1[1]
    x2, y2 = loc2[0], loc2[1]

    distance_x = abs(x2 - x1)
    if x1 == x2:
        distance_y1 = abs(y2 - y1)
        distance_y2 = distance_y1
    else:
        distance_y1 = (y_high - y1) + (y_high - y2)
        distance_y2 = (y1 - y_low) + (y2 - y_low)

    return int(distance_x + min(distance_y1, distance_y2))


def next_location(
    start_loc: list[float],
    list_locs: list[list[float]],
    y_low: float,
    y_high: float,
) -> tuple[list[list[float]], list[float], list[float], int]:
    """Pick the nearest next location and remove it from the candidate list."""
    list_dist = [distance_picking(start_loc, item, y_low, y_high) for item in list_locs]
    distance_next = min(list_dist)
    index_min = list_dist.index(distance_next)
    next_loc = list_locs[index_min]
    list_locs.remove(next_loc)
    return list_locs, start_loc, next_loc, distance_next


def create_picking_route(
    origin_loc: list[float], list_locs: list[list[float]], y_low: float, y_high: float
) -> tuple[int, list[list[float]]]:
    """Calculate route and total distance for a set of unique picking coordinates."""
    wave_distance = 0
    start_loc = origin_loc
    path = [start_loc]

    remaining = [list(item) for item in list_locs]
    while remaining:
        remaining, start_loc, next_loc, distance_next = next_location(start_loc, remaining, y_low, y_high)
        start_loc = next_loc
        path.append(start_loc)
        wave_distance += distance_next

    wave_distance += distance_picking(start_loc, origin_loc, y_low, y_high)
    path.append(origin_loc)
    return wave_distance, path


def parse_coord(value: str | list[float]) -> list[float]:
    if isinstance(value, str):
        return list(literal_eval(value))
    return list(value)
