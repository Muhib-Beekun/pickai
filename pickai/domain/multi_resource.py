from __future__ import annotations

from pickai.contracts import OptimizeConstraints, OptimizeRequest, OrderLine
from pickai.contracts.facility import FacilityProfile, ResourcePool
from pickai.domain.optimizer import optimize_wave


def _zone_for_x(x: float, zones: list) -> str | None:
    for zone in zones:
        if zone.x_min <= x <= zone.x_max:
            return zone.zone_id
    return None


def split_lines_by_zone(profile: FacilityProfile, lines: list[OrderLine], resource_count: int) -> list[tuple[str, list[OrderLine]]]:
    if not profile.zones or resource_count <= 1:
        return [("all", lines)]

    zone_buckets: dict[str, list[OrderLine]] = {z.zone_id: [] for z in profile.zones}
    for line in lines:
        zone_id = _zone_for_x(line.x, profile.zones) or profile.zones[0].zone_id
        zone_buckets[zone_id].append(line)

    active_zones = [zid for zid, bucket in zone_buckets.items() if bucket]
    if len(active_zones) <= resource_count:
        return [(zid, zone_buckets[zid]) for zid in active_zones]

    sorted_zones = sorted(active_zones, key=lambda zid: len(zone_buckets[zid]), reverse=True)
    merged: list[tuple[str, list[OrderLine]]] = []
    chunk_size = max(1, len(sorted_zones) // resource_count)
    for idx in range(0, len(sorted_zones), chunk_size):
        chunk_zones = sorted_zones[idx : idx + chunk_size]
        combined: list[OrderLine] = []
        for zid in chunk_zones:
            combined.extend(zone_buckets[zid])
        merged.append((",".join(chunk_zones), combined))
    return merged[:resource_count]


def detect_aisle_conflicts(assignments: list[dict]) -> list[str]:
    aisle_to_resources: dict[str, set[str]] = {}
    warnings: list[str] = []
    for assignment in assignments:
        resource_id = assignment["resource_id"]
        aisles = {line.get("aisle") or f"A{int(float(line.get('x', 0))) + 1}" for line in assignment.get("lines", [])}
        for aisle in aisles:
            aisle_to_resources.setdefault(aisle, set()).add(resource_id)

    for aisle, resources in aisle_to_resources.items():
        if len(resources) > 1:
            warnings.append(f"Aisle {aisle} shared by resources: {', '.join(sorted(resources))}")
    return warnings


def optimize_multi_resource(
    profile: FacilityProfile,
    lines: list[OrderLine],
    constraints: OptimizeConstraints,
    resources: ResourcePool | None,
    idempotency_key: str | None,
    resource_type: str = "picker",
) -> tuple[list[dict], list[str]]:
    pool = resources or profile.resources
    count = pool.pickers if resource_type == "picker" else pool.putters
    splits = split_lines_by_zone(profile, lines, count)

    assignments: list[dict] = []
    for idx, (zone_id, bucket) in enumerate(splits):
        if not bucket:
            continue
        resource_id = f"{resource_type}-{idx + 1}"
        request = OptimizeRequest(
            order_lines=bucket,
            constraints=constraints,
            idempotency_key=f"{idempotency_key or 'task'}-{resource_id}",
        )
        result = optimize_wave(request)
        assignments.append(
            {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "zone_id": zone_id,
                "order_lines": [line.line_id for line in bucket],
                "lines": [line.model_dump() for line in bucket],
                "result": result.model_dump(by_alias=True),
            }
        )

    warnings = detect_aisle_conflicts(assignments)
    return assignments, warnings
