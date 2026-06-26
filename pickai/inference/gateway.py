from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import httpx

from pickai.contracts import EquipmentMode, LadderState, OptimizeConstraints, OptimizeRequest


DEFAULT_MODEL = "qwen2.5:7b-instruct"
RETRY_MODEL = "qwen2.5:14b-instruct"
LOG_PATH = Path("logs/inference.jsonl")


def _log(task_type: str, model: str, latency_ms: int, status: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "task_type": task_type,
        "model": model,
        "latency_ms": latency_ms,
        "status": status,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _heuristic_parse_nl(text: str) -> tuple[dict, float]:
    lower = text.lower()
    equipment = "forklift" if "forklift" in lower else "walker"
    ladder_lock = "stay in aisle" in lower or "do not change aisle" in lower

    x_match = re.search(r"x\s*=\s*(-?\d+(?:\.\d+)?)", lower)
    y_match = re.search(r"y\s*=\s*(-?\d+(?:\.\d+)?)", lower)
    x = float(x_match.group(1)) if x_match else 0.0
    y = float(y_match.group(1)) if y_match else 5.5

    confidence = 0.95 if ("walker" in lower or "forklift" in lower) else 0.68
    parsed = {
        "constraints": {
            "equipment_mode": equipment,
            "ladder_must_stay_in_aisle": ladder_lock,
            "start_position": {"aisle": "A1", "level": "1", "x": x, "y": y},
        }
    }
    return parsed, confidence


def _ollama_generate(prompt: str, model: str) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    payload = {"model": model, "prompt": prompt, "stream": False}
    with httpx.Client(timeout=20) as client:
        resp = client.post(f"{base_url}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")


def run_task(task_type: str, payload: dict) -> dict:
    start = time.time()
    status = "ok"
    model_used = DEFAULT_MODEL

    try:
        if task_type == "nl_parse_optimize":
            text = payload.get("text", "")
            parsed, confidence = _heuristic_parse_nl(text)

            if confidence < 0.75:
                model_used = RETRY_MODEL
                # Best-effort retry for additional context; failure keeps heuristic output.
                try:
                    llm_text = _ollama_generate(
                        f"Return JSON only with constraints for optimizer request from: {text}",
                        RETRY_MODEL,
                    )
                    llm_json = json.loads(llm_text)
                    parsed = llm_json
                    confidence = 0.8
                except Exception:
                    pass

            constraints = OptimizeConstraints(
                equipment_mode=EquipmentMode(parsed["constraints"]["equipment_mode"]),
                ladder_must_stay_in_aisle=bool(parsed["constraints"].get("ladder_must_stay_in_aisle", False)),
                start_position=LadderState(**parsed["constraints"]["start_position"]),
            )
            return {
                "task_type": task_type,
                "confidence": confidence,
                "constraints": constraints.model_dump(),
            }

        if task_type == "explain_route":
            total_distance = payload.get("total_distance_m", 0)
            return {
                "task_type": task_type,
                "explanation": f"The computed route covers {total_distance:.1f} meters including aisle transitions.",
            }

        if task_type == "generate_synthetic_instruction":
            idx = payload.get("index", 0)
            return {
                "task_type": task_type,
                "instruction": f"Optimize wave {idx} using walker and start at x={idx % 10}, y={5.5 + (idx % 8)}",
            }

        raise ValueError(f"Unsupported task_type: {task_type}")
    except Exception as exc:
        status = f"error:{type(exc).__name__}"
        raise
    finally:
        latency_ms = int((time.time() - start) * 1000)
        _log(task_type, model_used, latency_ms, status)
