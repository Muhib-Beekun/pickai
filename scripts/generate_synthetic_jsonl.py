from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FULL = PROJECT_ROOT / "data" / "synthetic" / "synthetic_nl_parse.jsonl"
OUTPUT_SAMPLE = PROJECT_ROOT / "data" / "synthetic" / "sample.jsonl"


def build_row(row_id: int, wave_summary: dict) -> dict:
    equipment = random.choice(["walker", "forklift"])
    ladder_lock = random.choice([True, False])
    x = float(random.randint(0, 20))
    y = float(random.randint(6, 45))

    instruction = (
        f"Optimize this wave with {equipment}, start at x={x}, y={y}, "
        f"ladder {'must stay in aisle' if ladder_lock else 'can move between aisles'}."
    )

    output = {
        "constraints": {
            "equipment_mode": equipment,
            "ladder_must_stay_in_aisle": ladder_lock,
            "start_position": {"aisle": "A1", "level": "1", "x": x, "y": y},
        }
    }
    return {
        "instruction": instruction,
        "input": wave_summary,
        "output": output,
    }


def main() -> None:
    random.seed(42)
    source = PROJECT_ROOT / "data" / "fixtures" / "mendeley_sample.csv"
    df = pd.read_csv(source)

    OUTPUT_FULL.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for idx in range(2000):
        sample = df.sample(10, replace=True, random_state=idx)
        wave_summary = {
            "orders": int(sample["OrderNumber"].nunique()),
            "lines": int(len(sample)),
            "x_min": float(sample["x"].min()),
            "x_max": float(sample["x"].max()),
            "y_min": float(sample["y"].min()),
            "y_max": float(sample["y"].max()),
        }
        rows.append(build_row(idx, wave_summary))

    with OUTPUT_FULL.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    with OUTPUT_SAMPLE.open("w", encoding="utf-8") as f:
        for row in rows[:50]:
            f.write(json.dumps(row) + "\n")

    print(f"Generated {len(rows)} rows at {OUTPUT_FULL}")
    print(f"Wrote sample rows to {OUTPUT_SAMPLE}")


if __name__ == "__main__":
    main()
