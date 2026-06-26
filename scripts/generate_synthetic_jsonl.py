from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pickai.contracts import EquipmentMode, LadderState, OptimizeConstraints, OptimizeRequest, OrderLine
from pickai.domain.optimizer import optimize_wave

OUTPUT_FULL = PROJECT_ROOT / "data" / "synthetic" / "synthetic_nl_parse.jsonl"
OUTPUT_SAMPLE = PROJECT_ROOT / "data" / "synthetic" / "sample.jsonl"
DATASET_README = PROJECT_ROOT / "data" / "synthetic" / "README.md"


def _random_constraints(rng: random.Random) -> OptimizeConstraints:
    equipment = EquipmentMode.forklift if rng.random() > 0.5 else EquipmentMode.walker
    ladder_lock = bool(rng.randint(0, 1))
    x = float(rng.randint(0, 20))
    y = float(rng.randint(6, 45))
    return OptimizeConstraints(
        equipment_mode=equipment,
        ladder_must_stay_in_aisle=ladder_lock,
        start_position=LadderState(aisle=f"A{int(x)+1}", level=str(rng.randint(1, 4)), x=x, y=y),
    )


def _instruction_from_constraints(constraints: OptimizeConstraints, wave_size: int) -> str:
    lock_text = "must stay in aisle" if constraints.ladder_must_stay_in_aisle else "can cross aisles"
    start = constraints.start_position
    return (
        f"Optimize a wave with {wave_size} lines using {constraints.equipment_mode.value}. "
        f"Start at aisle {start.aisle} level {start.level}, x={start.x}, y={start.y}, and ladder {lock_text}."
    )


def _to_order_lines(df: pd.DataFrame) -> list[OrderLine]:
    lines: list[OrderLine] = []
    for idx, row in df.iterrows():
        lines.append(
            OrderLine(
                order_id=str(row["OrderNumber"]),
                line_id=str(idx),
                sku=str(row["SKU"]),
                location_id=f"loc-{idx}",
                quantity=int(row.get("PCS", 1)),
                x=float(row["x"]),
                y=float(row["y"]),
                level=str(row.get("level")) if row.get("level") is not None else None,
            )
        )
    return lines


def _aisle_for_x(x: float) -> str:
    return f"A{int(float(x)) + 1}"


def main() -> None:
    rng = random.Random(42)
    source = PROJECT_ROOT / "data" / "fixtures" / "mendeley_sample.csv"
    df = pd.read_csv(source)

    OUTPUT_FULL.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for idx in range(3000):
        sample_size = rng.randint(8, 25)
        sample = df.sample(sample_size, replace=True, random_state=1000 + idx).reset_index(drop=True)
        constraints = _random_constraints(rng)

        if constraints.ladder_must_stay_in_aisle:
            target_aisle = constraints.start_position.aisle
            same_aisle = df[df["x"].apply(lambda v: _aisle_for_x(float(v)) == target_aisle)]
            if same_aisle.empty:
                constraints.ladder_must_stay_in_aisle = False
            else:
                sample = same_aisle.sample(sample_size, replace=True, random_state=2000 + idx).reset_index(drop=True)

        order_lines = _to_order_lines(sample)

        request = OptimizeRequest(
            order_lines=order_lines,
            constraints=constraints,
            idempotency_key=f"synthetic-{idx}",
        )
        result = optimize_wave(request)

        wave_summary = {
            "orders": int(sample["OrderNumber"].nunique()),
            "lines": int(len(sample)),
            "x_min": float(sample["x"].min()),
            "x_max": float(sample["x"].max()),
            "y_min": float(sample["y"].min()),
            "y_max": float(sample["y"].max()),
        }

        row = {
            "instruction": _instruction_from_constraints(constraints, len(sample)),
            "input": wave_summary,
            "output": {
                "constraints": constraints.model_dump(mode="json"),
                "expected": {
                    "total_distance_m": result.total_distance_m,
                    "total_duration_s": result.total_duration_s,
                    "ladder_state_after": result.ladder_state_after.model_dump(mode="json") if result.ladder_state_after else None,
                },
            },
        }
        rows.append(row)

    with OUTPUT_FULL.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    with OUTPUT_SAMPLE.open("w", encoding="utf-8") as f:
        for row in rows[:50]:
            f.write(json.dumps(row) + "\n")

    DATASET_README.write_text(
        "\n".join(
            [
                "# Synthetic NL Parse Dataset",
                "",
                "This dataset is generated from deterministic optimizer outputs.",
                "Each row includes natural-language instruction, wave summary input, and ground-truth constraint JSON.",
                "Ground truth is produced by running PickAI domain optimizer over sampled fixture wave data.",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Generated {len(rows)} rows at {OUTPUT_FULL}")
    print(f"Sample written to {OUTPUT_SAMPLE}")


if __name__ == "__main__":
    main()
