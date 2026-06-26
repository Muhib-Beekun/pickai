from __future__ import annotations

import hashlib
import json


def row_key(row: dict) -> str:
    return row["instruction"] + json.dumps(row["input"], sort_keys=True)


def split_holdout(rows: list[dict], holdout_n: int = 100) -> tuple[list[dict], list[dict]]:
    if holdout_n >= len(rows):
        raise ValueError(f"holdout_n={holdout_n} must be smaller than dataset size {len(rows)}")

    ordered = sorted(rows, key=lambda row: hashlib.sha256(row_key(row).encode("utf-8")).hexdigest())
    holdout = ordered[:holdout_n]
    train = ordered[holdout_n:]
    return train, holdout
