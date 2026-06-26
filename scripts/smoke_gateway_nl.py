#!/usr/bin/env python
"""Quick gateway NL parse smoke for release checklist."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pickai.inference.gateway import run_task

CASES = [
    "Use forklift, start at aisle A3 level 2, x=2, y=8, ladder must stay in aisle",
    "Walker mode, start at aisle B1 level 1, x=5, y=12",
    "Batch wave size 40, equipment walker, ladder can move between aisles",
]

if __name__ == "__main__":
    for i, text in enumerate(CASES, 1):
        result = run_task("nl_parse_optimize", {"text": text})
        c = result["constraints"]
        start = c.get("start_position") or {}
        print(
            f"case{i}: equipment={c.get('equipment_mode')} "
            f"ladder_stay={c.get('ladder_must_stay_in_aisle')} "
            f"start_aisle={start.get('aisle')}"
        )
