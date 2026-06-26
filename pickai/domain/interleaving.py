from __future__ import annotations

from pickai.contracts import OptimizeConstraints
from pickai.contracts.facility import FacilityProfile, ResourcePool
from pickai.contracts.types import OrderLine
from pickai.domain.multi_resource import optimize_multi_resource


def interleave_tasks(
    profile: FacilityProfile,
    pick_lines: list[OrderLine],
    put_lines: list[OrderLine],
    replen_lines: list[OrderLine],
    constraints: OptimizeConstraints,
    run_id: str,
    weight_by_line_id: dict[str, float] | None = None,
) -> tuple[list[dict], list[str]]:
    """Combine pick, put, replen based on interleaving policy."""
    mode = profile.task_interleaving
    assignments: list[dict] = []
    warnings: list[str] = []

    if mode == "off":
        for batch, rtype in [(pick_lines, "picker"), (put_lines, "putter"), (replen_lines, "putter")]:
            if not batch:
                continue
            batch_assignments, w = optimize_multi_resource(
                profile, batch, constraints, profile.resources, f"{run_id}-{rtype}", resource_type=rtype
            )
            assignments.extend(batch_assignments)
            warnings.extend(w)
        return assignments, warnings

    def _zone_key(line: OrderLine) -> str:
        for z in profile.zones:
            if z.x_min <= line.x <= z.x_max:
                return z.zone_id
        return "all"

    if mode == "same_zone":
        zone_tasks: dict[str, list[OrderLine]] = {}
        for line in pick_lines + put_lines + replen_lines:
            zone_tasks.setdefault(_zone_key(line), []).append(line)
        for zid, batch in zone_tasks.items():
            if not batch:
                continue
            batch_assignments, w = optimize_multi_resource(
                profile,
                batch,
                constraints,
                ResourcePool(pickers=1, putters=1),
                f"{run_id}-zone-{zid}",
                resource_type="picker",
            )
            assignments.extend(batch_assignments)
            warnings.extend(w)
        return assignments, warnings

    # aggressive: merge all task types into one optimized trip per cart batch
    merged = pick_lines + put_lines + replen_lines
    if merged:
        batch_assignments, w = optimize_multi_resource(
            profile, merged, constraints, profile.resources, f"{run_id}-interleaved", resource_type="picker"
        )
        assignments.extend(batch_assignments)
        warnings.extend(w)
    return assignments, warnings
