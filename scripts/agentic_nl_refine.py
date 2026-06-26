from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SYNTHETIC_PATH = PROJECT_ROOT / "data" / "synthetic" / "synthetic_nl_parse.jsonl"
REFINED_PATH = PROJECT_ROOT / "data" / "synthetic" / "refined_nl_parse.jsonl"
LOG_PATH = PROJECT_ROOT / "logs" / "agentic_refine.jsonl"
BASE_MODEL = os.getenv("PICKAI_BASE_MODEL", "qwen2.5:7b-instruct")


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _ollama(prompt: str) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    payload = {"model": BASE_MODEL, "prompt": prompt, "stream": False}
    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{base_url}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")


def _writer(instruction: str, wave_input: dict, feedback: str | None) -> dict:
    prompt = (
        "Return JSON only with top-level key constraints and fields: equipment_mode, "
        "ladder_must_stay_in_aisle, start_position{aisle,level,x,y}.\n"
        f"Instruction: {instruction}\n"
        f"Wave: {json.dumps(wave_input)}\n"
    )
    if feedback:
        prompt += f"Validator feedback: {feedback}\n"
    output = _ollama(prompt)
    parsed = _extract_json(output)
    return parsed.get("constraints", {}) if isinstance(parsed, dict) else {}


def _normalize(c: dict) -> dict:
    start = c.get("start_position", {}) if isinstance(c, dict) else {}
    return {
        "equipment_mode": str(c.get("equipment_mode", "")).lower(),
        "ladder_must_stay_in_aisle": bool(c.get("ladder_must_stay_in_aisle", False)),
        "start_position": {
            "aisle": str(start.get("aisle", "")),
            "level": str(start.get("level", "")),
            "x": float(start.get("x", 0.0)) if str(start.get("x", "")).strip() != "" else 0.0,
            "y": float(start.get("y", 0.0)) if str(start.get("y", "")).strip() != "" else 0.0,
        },
    }


def _validator(pred: dict, truth: dict) -> tuple[float, str]:
    p = _normalize(pred)
    t = _normalize(truth)
    checks = []
    checks.append(("equipment_mode", p["equipment_mode"] == t["equipment_mode"]))
    checks.append(("ladder_must_stay_in_aisle", p["ladder_must_stay_in_aisle"] == t["ladder_must_stay_in_aisle"]))
    checks.append(("start_position.aisle", p["start_position"]["aisle"] == t["start_position"]["aisle"]))
    checks.append(("start_position.level", p["start_position"]["level"] == t["start_position"]["level"]))
    checks.append(("start_position.x", abs(p["start_position"]["x"] - t["start_position"]["x"]) < 1e-6))
    checks.append(("start_position.y", abs(p["start_position"]["y"] - t["start_position"]["y"]) < 1e-6))

    score = sum(1.0 for _, ok in checks if ok) / len(checks)
    failed = [name for name, ok in checks if not ok]
    feedback = "All fields matched." if not failed else "Fix fields: " + ", ".join(failed)
    return score, feedback


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    rows = [json.loads(line) for line in SYNTHETIC_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    held_out = rows[-args.limit :]

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    REFINED_PATH.parent.mkdir(parents=True, exist_ok=True)

    refined_rows = []
    with LOG_PATH.open("a", encoding="utf-8") as logf:
        for idx, row in enumerate(held_out):
            truth = row["output"]["constraints"]
            feedback = None
            best_pred = None
            best_score = -1.0

            for cycle in range(1, 4):
                pred = _writer(row["instruction"], row["input"], feedback)
                score, feedback = _validator(pred, truth)
                logf.write(
                    json.dumps(
                        {
                            "index": idx,
                            "cycle": cycle,
                            "score": score,
                            "feedback": feedback,
                        }
                    )
                    + "\n"
                )
                if score > best_score:
                    best_score = score
                    best_pred = pred

            if best_score >= 0.8:
                refined_rows.append(
                    {
                        "instruction": row["instruction"],
                        "input": row["input"],
                        "output": {"constraints": best_pred},
                    }
                )

            if (idx + 1) % 10 == 0:
                print(f"Processed {idx + 1}/{len(held_out)}", flush=True)

    with REFINED_PATH.open("w", encoding="utf-8") as f:
        for row in refined_rows:
            f.write(json.dumps(row) + "\n")

    print(f"Processed {len(held_out)} examples")
    print(f"Refined examples saved: {len(refined_rows)}")


if __name__ == "__main__":
    main()
