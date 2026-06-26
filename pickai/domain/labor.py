from __future__ import annotations

from pickai.contracts.facility import FacilityLocation, FacilityProfile
from pickai.contracts.types import OrderLine
from pickai.domain.equipment import infer_aisle_id


def pick_height_penalty_s(loc: FacilityLocation | None, golden_min: float, golden_max: float, penalty_per_m: float) -> float:
    if loc is None or loc.attributes.pick_height_m is None:
        return 0.0
    h = loc.attributes.pick_height_m
    if golden_min <= h <= golden_max:
        return 0.0
    return abs(h - golden_max if h > golden_max else h - golden_min) * penalty_per_m


def estimate_labor_s(
    profile: FacilityProfile,
    line_count: int,
    travel_duration_s: float,
    locations_by_id: dict[str, FacilityLocation],
    picked_lines: list[OrderLine],
) -> float:
    cfg = profile.labor
    base = line_count * cfg.base_pick_s
    height_penalty = 0.0
    for line in picked_lines:
        loc = locations_by_id.get(line.location_id)
        height_penalty += pick_height_penalty_s(loc, cfg.golden_zone_min_m, cfg.golden_zone_max_m, cfg.height_penalty_per_m)
    return travel_duration_s + base + height_penalty
