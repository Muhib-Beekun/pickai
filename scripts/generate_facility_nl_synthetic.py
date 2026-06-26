from __future__ import annotations

import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pickai.contracts.facility import AisleDirection, FacilityProfile
from pickai.facility.defaults import build_default_profile

OUTPUT = PROJECT_ROOT / "data" / "synthetic" / "synthetic_facility_nl.jsonl"

PROMPT_HEADER = (
    "Return JSON only with key `facility_patch` containing optional fields: "
    "aisles[{aisle_id,direction,blocked}], resources{pickers,putters}, "
    "picking_method, task_interleaving, cart_max_lines.\n"
)


def _instruction(patch: dict) -> str:
    parts = []
    if "aisles" in patch:
        for aisle in patch["aisles"]:
            parts.append(f"aisle {aisle['aisle_id']} {aisle['direction']}")
            if aisle.get("blocked"):
                parts.append(f"block {aisle['aisle_id']}")
    if "resources" in patch:
        r = patch["resources"]
        parts.append(f"use {r['pickers']} pickers and {r['putters']} putters")
    if "picking_method" in patch:
        parts.append(f"{patch['picking_method']} picking")
    if "task_interleaving" in patch:
        parts.append(f"interleaving {patch['task_interleaving']}")
    if "cart_max_lines" in patch:
        parts.append(f"cart max {patch['cart_max_lines']} lines")
    return "Configure facility: " + ", ".join(parts) + "."


def main() -> None:
    rng = random.Random(99)
    profile = build_default_profile()
    rows: list[dict] = []

    for idx in range(1500):
        patch: dict = {}
        if rng.random() > 0.3:
            aisle = profile.aisles[rng.randint(0, len(profile.aisles) - 1)]
            direction = rng.choice(["increasing", "decreasing", "two_way"])
            patch["aisles"] = [{"aisle_id": aisle.aisle_id, "direction": direction, "blocked": bool(rng.randint(0, 1) == 1 and rng.random() > 0.85)}]
        if rng.random() > 0.4:
            patch["resources"] = {"pickers": rng.randint(1, 4), "putters": rng.randint(1, 3)}
        if rng.random() > 0.5:
            patch["picking_method"] = rng.choice(["discrete", "batch", "wave", "zone"])
        if rng.random() > 0.6:
            patch["task_interleaving"] = rng.choice(["off", "same_zone", "aggressive"])
        if rng.random() > 0.7:
            patch["cart_max_lines"] = rng.randint(20, 80)

        if not patch:
            continue

        rows.append(
            {
                "instruction": _instruction(patch),
                "input": {"facility_id": profile.facility_id, "version": profile.version},
                "output": {"facility_patch": patch},
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
