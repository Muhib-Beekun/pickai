from __future__ import annotations

from collections import defaultdict

from pickai.contracts import OrderLine
from pickai.contracts.facility import FacilityProfile, HeatLayer, HeatMap, HeatPoint
from pickai.domain.routing import distance_picking


def _staging_point(profile: FacilityProfile) -> tuple[float, float]:
    layout = profile.layout
    sx = layout.staging_x if layout.staging_x is not None else layout.origin_x
    sy = layout.staging_y if layout.staging_y is not None else layout.origin_y
    return float(sx), float(sy)


def compute_pick_density(profile: FacilityProfile, lines: list[OrderLine]) -> HeatMap:
    counts: dict[str, int] = defaultdict(int)
    coords: dict[str, tuple[float, float]] = {}
    for line in lines:
        counts[line.location_id] += line.quantity
        coords[line.location_id] = (line.x, line.y)

    points: list[HeatPoint] = []
    max_value = 0.0
    for loc in profile.locations:
        value = float(counts.get(loc.location_id, 0))
        max_value = max(max_value, value)
        points.append(HeatPoint(location_id=loc.location_id, x=loc.x, y=loc.y, value=value))

    for loc_id, count in counts.items():
        if loc_id not in {p.location_id for p in points}:
            x, y = coords[loc_id]
            max_value = max(max_value, float(count))
            points.append(HeatPoint(location_id=loc_id, x=x, y=y, value=float(count)))

    return HeatMap(layer=HeatLayer.pick_density, points=points, max_value=max_value)


def compute_walk_burden(profile: FacilityProfile) -> HeatMap:
    staging = _staging_point(profile)
    y_low = profile.layout.y_low
    y_high = profile.layout.y_high
    points: list[HeatPoint] = []
    max_value = 0.0
    for loc in profile.locations:
        dist = float(distance_picking(list(staging), [loc.x, loc.y], y_low, y_high))
        max_value = max(max_value, dist)
        points.append(HeatPoint(location_id=loc.location_id, x=loc.x, y=loc.y, value=dist))
    return HeatMap(layer=HeatLayer.walk_burden, points=points, max_value=max_value)


def compute_congestion(profile: FacilityProfile, assignments: list[dict]) -> HeatMap:
    """Predict aisle overlap from multi-resource route endpoints."""
    aisle_hits: dict[str, float] = defaultdict(float)
    for assignment in assignments:
        for line in assignment.get("lines", []):
            aisle = line.get("aisle") or f"A{int(float(line.get('x', 0))) + 1}"
            aisle_hits[aisle] += 1.0

    points: list[HeatPoint] = []
    max_value = 0.0
    for loc in profile.locations:
        aisle = loc.aisle or f"A{int(loc.x) + 1}"
        value = float(aisle_hits.get(aisle, 0))
        max_value = max(max_value, value)
        points.append(HeatPoint(location_id=loc.location_id, x=loc.x, y=loc.y, value=value))
    return HeatMap(layer=HeatLayer.congestion, points=points, max_value=max_value)


def build_heat_maps(
    profile: FacilityProfile,
    lines: list[OrderLine],
    assignments: list[dict] | None = None,
) -> list[HeatMap]:
    layers = {layer.value for layer in profile.heat_config.layers}
    maps: list[HeatMap] = []
    if HeatLayer.pick_density.value in layers:
        maps.append(compute_pick_density(profile, lines))
    if HeatLayer.walk_burden.value in layers:
        maps.append(compute_walk_burden(profile))
    if HeatLayer.congestion.value in layers and assignments:
        maps.append(compute_congestion(profile, assignments))
    return maps
