from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EquipmentProfile:
    speed_mps: float
    turn_penalty_s: float
    relocate_penalty_distance_m: float
    relocate_penalty_s: float
    vertical_pick_s: float


PROFILES: dict[str, EquipmentProfile] = {
    "walker": EquipmentProfile(
        speed_mps=1.4,
        turn_penalty_s=1.0,
        relocate_penalty_distance_m=6.0,
        relocate_penalty_s=8.0,
        vertical_pick_s=6.0,
    ),
    "forklift": EquipmentProfile(
        speed_mps=2.5,
        turn_penalty_s=2.5,
        relocate_penalty_distance_m=10.0,
        relocate_penalty_s=14.0,
        vertical_pick_s=3.5,
    ),
}


def infer_aisle_id(point: list[float]) -> str:
    aisle_num = int(point[0]) + 1
    return f"A{max(1, aisle_num)}"


def load_aisle_rules(path: str | Path = "data/fixtures/aisle_rules.json") -> dict[str, str]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("one_way", {})


def forklift_direction_penalty(from_point: list[float], to_point: list[float], one_way_rules: dict[str, str]) -> float:
    aisle = infer_aisle_id(from_point)
    rule = one_way_rules.get(aisle)
    if not rule:
        return 0.0

    if rule == "increasing" and to_point[1] < from_point[1]:
        return 6.0
    if rule == "decreasing" and to_point[1] > from_point[1]:
        return 6.0
    return 0.0
