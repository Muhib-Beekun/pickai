from __future__ import annotations

from pickai.domain.routing import distance_picking


def _aisle_key(x: float) -> float:
    return round(float(x), 4)


def _group_by_aisle(locations: list[list[float]]) -> dict[float, list[list[float]]]:
    groups: dict[float, list[list[float]]] = {}
    for loc in locations:
        key = _aisle_key(loc[0])
        groups.setdefault(key, []).append(loc)
    return groups


def _visit_aisle_locs(
    aisle_x: float,
    locs: list[list[float]],
    enter_high: bool,
    y_low: float,
    y_high: float,
) -> tuple[list[list[float]], float]:
    """Traverse one aisle visiting all y positions (return policy within aisle)."""
    sorted_locs = sorted(locs, key=lambda p: p[1], reverse=enter_high)
    path: list[list[float]] = []
    dist = 0.0
    prev = [aisle_x, y_high if enter_high else y_low]
    for loc in sorted_locs:
        dist += float(distance_picking(prev, loc, y_low, y_high))
        path.append(loc)
        prev = loc
    return path, dist


def route_s_shape(
    origin: list[float],
    locations: list[list[float]],
    y_low: float,
    y_high: float,
) -> tuple[float, list[list[float]]]:
    """S-shape: enter each aisle from alternating ends."""
    if not locations:
        return 0.0, [list(origin), list(origin)]

    groups = _group_by_aisle(locations)
    aisle_keys = sorted(groups.keys())
    path: list[list[float]] = [list(origin)]
    total = 0.0
    cursor = list(origin)
    enter_high = True

    for aisle_x in aisle_keys:
        aisle_locs = groups[aisle_x]
        entry = [aisle_x, y_high if enter_high else y_low]
        total += float(distance_picking(cursor, entry, y_low, y_high))
        cursor = entry
        aisle_path, aisle_dist = _visit_aisle_locs(aisle_x, aisle_locs, enter_high, y_low, y_high)
        total += aisle_dist
        path.extend(aisle_path)
        if aisle_path:
            cursor = aisle_path[-1]
        enter_high = not enter_high

    total += float(distance_picking(cursor, origin, y_low, y_high))
    path.append(list(origin))
    return total, path


def route_return(
    origin: list[float],
    locations: list[list[float]],
    y_low: float,
    y_high: float,
) -> tuple[float, list[list[float]]]:
    """Return policy: enter each aisle from nearest end, return along aisle."""
    if not locations:
        return 0.0, [list(origin), list(origin)]

    groups = _group_by_aisle(locations)
    aisle_keys = sorted(groups.keys(), key=lambda ax: abs(ax - origin[0]))
    path: list[list[float]] = [list(origin)]
    total = 0.0
    cursor = list(origin)

    for aisle_x in aisle_keys:
        aisle_locs = groups[aisle_x]
        avg_y = sum(p[1] for p in aisle_locs) / len(aisle_locs)
        enter_high = avg_y >= (y_low + y_high) / 2
        entry = [aisle_x, y_high if enter_high else y_low]
        total += float(distance_picking(cursor, entry, y_low, y_high))
        aisle_path, aisle_dist = _visit_aisle_locs(aisle_x, aisle_locs, enter_high, y_low, y_high)
        total += aisle_dist
        path.extend(aisle_path)
        cursor = aisle_path[-1] if aisle_path else entry
        exit_pt = [aisle_x, y_low if enter_high else y_high]
        total += float(distance_picking(cursor, exit_pt, y_low, y_high))
        cursor = exit_pt

    total += float(distance_picking(cursor, origin, y_low, y_high))
    path.append(list(origin))
    return total, path


def route_largest_gap(
    origin: list[float],
    locations: list[list[float]],
    y_low: float,
    y_high: float,
) -> tuple[float, list[list[float]]]:
    """Largest-gap: skip the biggest intra-aisle gap when traversing."""
    if not locations:
        return 0.0, [list(origin), list(origin)]

    pruned: list[list[float]] = []
    groups = _group_by_aisle(locations)
    for aisle_x, locs in groups.items():
        if len(locs) <= 2:
            pruned.extend(locs)
            continue
        sorted_y = sorted(locs, key=lambda p: p[1])
        gaps = [(sorted_y[i + 1][1] - sorted_y[i][1], i) for i in range(len(sorted_y) - 1)]
        _, skip_idx = max(gaps, key=lambda g: g[0])
        pruned.extend(sorted_y[: skip_idx + 1])
        pruned.extend(sorted_y[skip_idx + 2 :])

    return route_return(origin, pruned, y_low, y_high)


def route_combined(
    origin: list[float],
    locations: list[list[float]],
    y_low: float,
    y_high: float,
) -> tuple[float, list[list[float]]]:
    """Pick shorter of S-shape and return policies."""
    d_s, p_s = route_s_shape(origin, locations, y_low, y_high)
    d_r, p_r = route_return(origin, locations, y_low, y_high)
    return (d_s, p_s) if d_s <= d_r else (d_r, p_r)


def build_route_by_policy(
    policy: str,
    origin: list[float],
    locations: list[list[float]],
    y_low: float,
    y_high: float,
) -> tuple[float, list[list[float]]]:
    policy = (policy or "shortest_path").lower()
    if policy == "s_shape":
        return route_s_shape(origin, locations, y_low, y_high)
    if policy == "largest_gap":
        return route_largest_gap(origin, locations, y_low, y_high)
    if policy == "combined":
        return route_combined(origin, locations, y_low, y_high)
    if policy in ("return", "return_policy"):
        return route_return(origin, locations, y_low, y_high)
    return route_combined(origin, locations, y_low, y_high)
