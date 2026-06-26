from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from pickai.contracts.facility import (
    FacilityProfile,
    PickHistoryRecord,
    SlottingSuggestion,
    VelocityTier,
)
from pickai.domain.routing import distance_picking


class PickHistoryStore:
    def __init__(self, root: str | Path = "data/facilities") -> None:
        self.root = Path(root)

    def _path(self, tenant_id: str, facility_id: str) -> Path:
        return self.root / tenant_id / f"{facility_id}_pick_history.jsonl"

    def load(self, tenant_id: str = "default", facility_id: str = "main") -> list[PickHistoryRecord]:
        path = self._path(tenant_id, facility_id)
        if not path.exists():
            return []
        return [PickHistoryRecord.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def save(self, tenant_id: str, facility_id: str, records: list[PickHistoryRecord]) -> int:
        path = self._path(tenant_id, facility_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(r.model_dump_json() for r in records) + "\n", encoding="utf-8")
        return len(records)

    def import_csv(self, tenant_id: str, facility_id: str, csv_content: str) -> int:
        reader = csv.DictReader(csv_content.splitlines())
        records: list[PickHistoryRecord] = []
        for row in reader:
            records.append(
                PickHistoryRecord(
                    order_id=str(row.get("order_id", row.get("OrderNumber", ""))),
                    sku=str(row.get("sku", row.get("SKU", ""))),
                    location_id=str(row.get("location_id", "")),
                    quantity=int(float(row.get("quantity", row.get("PCS", 1)))),
                    x=float(row.get("x", 0)),
                    y=float(row.get("y", 0)),
                )
            )
        return self.save(tenant_id, facility_id, records)


pick_history_store = PickHistoryStore()


def classify_abc(records: list[PickHistoryRecord]) -> dict[str, VelocityTier]:
    sku_picks: dict[str, int] = defaultdict(int)
    for r in records:
        sku_picks[r.sku] += r.quantity
    ranked = sorted(sku_picks.items(), key=lambda x: x[1], reverse=True)
    total = sum(c for _, c in ranked) or 1
    tiers: dict[str, VelocityTier] = {}
    cumulative = 0.0
    for sku, count in ranked:
        share = count / total
        if cumulative < 0.8:
            tiers[sku] = VelocityTier.A
        elif cumulative < 0.95:
            tiers[sku] = VelocityTier.B
        else:
            tiers[sku] = VelocityTier.C
        cumulative += share
    return tiers


def compute_sku_affinity(records: list[PickHistoryRecord]) -> dict[str, dict[str, float]]:
    """Co-pick frequency by SKU pair within same order."""
    order_skus: dict[str, set[str]] = defaultdict(set)
    for r in records:
        order_skus[r.order_id].add(r.sku)
    affinity: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for skus in order_skus.values():
        sku_list = sorted(skus)
        for i, a in enumerate(sku_list):
            for b in sku_list[i + 1 :]:
                affinity[a][b] += 1.0
                affinity[b][a] += 1.0
    return {k: dict(v) for k, v in affinity.items()}


def generate_slotting_suggestions(
    profile: FacilityProfile,
    records: list[PickHistoryRecord],
    top_n: int = 10,
) -> list[SlottingSuggestion]:
    if not records:
        return []

    tiers = classify_abc(records)
    affinity = compute_sku_affinity(records)
    staging = (
        profile.layout.staging_x or profile.layout.origin_x,
        profile.layout.staging_y or profile.layout.origin_y,
    )
    y_low, y_high = profile.layout.y_low, profile.layout.y_high

    loc_by_id = {loc.location_id: loc for loc in profile.locations}
    sku_loc: dict[str, tuple[str, float, float]] = {}
    for r in records:
        sku_loc[r.sku] = (r.location_id, r.x, r.y)

    a_skus = [s for s, t in tiers.items() if t == VelocityTier.A]
    suggestions: list[SlottingSuggestion] = []

    near_slots = sorted(
        profile.locations,
        key=lambda loc: float(distance_picking(list(staging), [loc.x, loc.y], y_low, y_high)),
    )

    used_targets: set[str] = set()
    for sku in a_skus[:top_n]:
        current = sku_loc.get(sku)
        if not current:
            continue
        cur_loc_id, cx, cy = current
        cur_burden = float(distance_picking(list(staging), [cx, cy], y_low, y_high))
        target = next((s for s in near_slots if s.location_id not in used_targets and s.location_id != cur_loc_id), None)
        if not target:
            break
        new_burden = float(distance_picking(list(staging), [target.x, target.y], y_low, y_high))
        saved = cur_burden - new_burden
        if saved <= 0:
            continue
        reason = f"ABC tier {tiers[sku].value}: move fast mover closer to staging"
        partners = sorted(affinity.get(sku, {}).items(), key=lambda x: x[1], reverse=True)[:2]
        if partners:
            reason += f"; affinity with {', '.join(p[0] for p in partners)}"
        suggestions.append(
            SlottingSuggestion(
                sku=sku,
                from_location_id=cur_loc_id,
                to_location_id=target.location_id,
                walk_burden_saved_m=round(saved, 2),
                reason=reason,
            )
        )
        used_targets.add(target.location_id)

    return suggestions
