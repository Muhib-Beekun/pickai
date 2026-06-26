from __future__ import annotations

from collections import defaultdict

from pickai.contracts.facility import FacilityProfile, PickingMethod
from pickai.contracts.types import OrderLine


def split_discrete(lines: list[OrderLine]) -> list[list[OrderLine]]:
    by_order: dict[str, list[OrderLine]] = defaultdict(list)
    for line in lines:
        by_order[line.order_id].append(line)
    return list(by_order.values())


def split_batch(lines: list[OrderLine], max_lines: int, max_weight_kg: float) -> list[list[OrderLine]]:
    batches: list[list[OrderLine]] = []
    current: list[OrderLine] = []
    weight = 0.0
    for line in lines:
        line_weight = float(line.weight_kg or 1.0) * line.quantity
        if current and (len(current) >= max_lines or weight + line_weight > max_weight_kg):
            batches.append(current)
            current = []
            weight = 0.0
        current.append(line)
        weight += line_weight
    if current:
        batches.append(current)
    return batches


def split_wave(lines: list[OrderLine]) -> list[list[OrderLine]]:
    return [lines] if lines else []


def split_by_picking_method(
    profile: FacilityProfile,
    lines: list[OrderLine],
    weight_by_line_id: dict[str, float] | None = None,
) -> list[list[OrderLine]]:
    enriched: list[OrderLine] = []
    for line in lines:
        w = weight_by_line_id.get(line.line_id) if weight_by_line_id else None
        enriched.append(line if w is None else line.model_copy(update={"weight_kg": w}))

    method = profile.picking_method
    if method == PickingMethod.discrete:
        return split_discrete(enriched)
    if method == PickingMethod.batch:
        return split_batch(enriched, profile.cart_max_lines, profile.cart_max_weight_kg)
    return split_wave(enriched)
