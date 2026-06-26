from __future__ import annotations

from pickai.contracts.types import OrderLine


def split_cart_capacity(
    lines: list[OrderLine],
    max_lines: int,
    max_weight_kg: float,
    max_pieces: int,
    weight_by_line_id: dict[str, float] | None = None,
) -> list[list[OrderLine]]:
    """Split lines into cart-feasible batches."""
    batches: list[list[OrderLine]] = []
    current: list[OrderLine] = []
    weight = 0.0
    pieces = 0

    for line in lines:
        w = float((weight_by_line_id or {}).get(line.line_id, line.weight_kg if line.weight_kg is not None else 1.0))
        line_weight = w * line.quantity
        line_pieces = line.quantity
        overflow = (
            current
            and (
                len(current) >= max_lines
                or weight + line_weight > max_weight_kg
                or pieces + line_pieces > max_pieces
            )
        )
        if overflow:
            batches.append(current)
            current = []
            weight = 0.0
            pieces = 0
        current.append(line)
        weight += line_weight
        pieces += line_pieces

    if current:
        batches.append(current)
    return batches if batches else ([lines] if lines else [])
