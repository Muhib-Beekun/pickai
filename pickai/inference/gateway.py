from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx

from pickai.contracts import EquipmentMode, LadderState, OptimizeConstraints, OptimizeRequest
from pickai.domain.optimizer import optimize_wave

DEFAULT_MODEL = "qwen2.5:7b-instruct"
LOCAL_LORA_DIR = os.getenv("PICKAI_LOCAL_LORA_DIR", str(Path("outputs/lora")))
USE_LOCAL_LORA = os.getenv("PICKAI_USE_LORA", "0") == "1"
LOG_PATH = Path("logs/inference.jsonl")
_LOCAL_LORA_GENERATOR: tuple[object, object] | None = None


def _log(task_type: str, model: str, latency_ms: int, status: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "task_type": task_type,
                    "model": model,
                    "latency_ms": latency_ms,
                    "status": status,
                }
            )
            + "\n"
        )


from pickai.inference.nl_parse_extract import extract_constraints_json
from pickai.inference.nl_parse_prompt import build_nl_parse_prompt


def _heuristic_parse(text: str) -> dict:
    lower = text.lower()
    equipment = "forklift" if "forklift" in lower else "walker"
    ladder_lock = "stay in aisle" in lower or "do not change aisle" in lower
    x_match = re.search(r"x\s*=\s*(-?\d+(?:\.\d+)?)", lower)
    y_match = re.search(r"y\s*=\s*(-?\d+(?:\.\d+)?)", lower)
    x = float(x_match.group(1)) if x_match else 0.0
    y = float(y_match.group(1)) if y_match else 5.5
    return {
        "constraints": {
            "equipment_mode": equipment,
            "ladder_must_stay_in_aisle": ladder_lock,
            "start_position": {"aisle": "A1", "level": "1", "x": x, "y": y},
        }
    }


def _ollama_generate(prompt: str, model: str) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    payload = {"model": model, "prompt": prompt, "stream": False}
    with httpx.Client(timeout=30) as client:
        response = client.post(f"{base_url}/api/generate", json=payload)
        response.raise_for_status()
        return response.json().get("response", "")


def _load_local_lora() -> tuple[object, object]:
    global _LOCAL_LORA_GENERATOR
    if _LOCAL_LORA_GENERATOR is not None:
        return _LOCAL_LORA_GENERATOR

    import torch
    from peft import AutoPeftModelForCausalLM
    from transformers import AutoTokenizer

    os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

    tokenizer = AutoTokenizer.from_pretrained(LOCAL_LORA_DIR, trust_remote_code=True)
    model = AutoPeftModelForCausalLM.from_pretrained(
        LOCAL_LORA_DIR,
        torch_dtype=torch.float16,
        trust_remote_code=True,
        device_map="auto",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    _LOCAL_LORA_GENERATOR = (tokenizer, model)
    return _LOCAL_LORA_GENERATOR


def _generate(prompt: str, model: str) -> str:
    if USE_LOCAL_LORA and Path(LOCAL_LORA_DIR).exists():
        import torch

        tokenizer, local_model = _load_local_lora()
        encoded = tokenizer(prompt, return_tensors="pt").to(local_model.device)
        with torch.inference_mode():
            output = local_model.generate(
                **encoded,
                max_new_tokens=160,
                do_sample=False,
                temperature=None,
                pad_token_id=tokenizer.eos_token_id,
            )
        return tokenizer.decode(output[0][encoded["input_ids"].shape[1] :], skip_special_tokens=True)
    return _ollama_generate(prompt, model)


def _writer_prompt(text: str, feedback: str | None, wave_input: dict | None = None) -> str:
    prompt = build_nl_parse_prompt(text, wave_input or {})
    if feedback:
        prompt += f"\nValidator feedback: {feedback}\n"
    return prompt


def _validate_constraints(parsed: dict) -> tuple[bool, str]:
    try:
        constraints = parsed.get("constraints", parsed)
        OptimizeConstraints(
            equipment_mode=EquipmentMode(constraints["equipment_mode"]),
            ladder_must_stay_in_aisle=bool(constraints.get("ladder_must_stay_in_aisle", False)),
            start_position=LadderState(**constraints["start_position"]),
        )
        return True, "valid"
    except Exception as exc:
        return False, f"invalid constraints: {exc}"


def _parse_with_dual_agent(text: str, model: str) -> tuple[dict, float]:
    best = _heuristic_parse(text)
    best_score = 0.2
    feedback = None

    for cycle in range(3):
        response = _generate(_writer_prompt(text, feedback, {"source": "gateway"}), model)
        parsed = {"constraints": extract_constraints_json(response)}
        is_valid, feedback = _validate_constraints(parsed)
        score = 1.0 if is_valid else max(0.0, 0.7 - (cycle * 0.2))
        if score > best_score:
            best = parsed if parsed else best
            best_score = score
        if is_valid:
            break

    if "constraints" not in best:
        best = _heuristic_parse(text)
    return best, best_score


def run_task(task_type: str, payload: dict) -> dict:
    start = time.time()
    status = "ok"
    model_used = LOCAL_LORA_DIR if USE_LOCAL_LORA and Path(LOCAL_LORA_DIR).exists() else DEFAULT_MODEL

    try:
        if task_type == "nl_parse_optimize":
            text = payload.get("text", "")
            parsed, confidence = _parse_with_dual_agent(text, DEFAULT_MODEL)
            constraints_raw = parsed.get("constraints", parsed)
            constraints = OptimizeConstraints(
                equipment_mode=EquipmentMode(constraints_raw["equipment_mode"]),
                ladder_must_stay_in_aisle=bool(constraints_raw.get("ladder_must_stay_in_aisle", False)),
                start_position=LadderState(**constraints_raw["start_position"]),
            )
            return {
                "task_type": task_type,
                "confidence": confidence,
                "constraints": constraints.model_dump(mode="json"),
            }

        if task_type == "call_compute_optimal_pick_path":
            request = OptimizeRequest(**payload)
            result = optimize_wave(request)
            return {
                "task_type": task_type,
                "result": result.model_dump(by_alias=True),
            }

        if task_type == "explain_route":
            total_distance = payload.get("total_distance_m", 0)
            return {
                "task_type": task_type,
                "explanation": f"The optimized route distance is {total_distance:.1f}m with deterministic solver ordering.",
            }

        if task_type == "generate_synthetic_instruction":
            idx = payload.get("index", 0)
            return {
                "task_type": task_type,
                "instruction": f"Optimize wave {idx} with forklift and start x={idx % 12}, y={7 + (idx % 5)}",
            }

        raise ValueError(f"Unsupported task_type: {task_type}")
    except Exception as exc:
        status = f"error:{type(exc).__name__}"
        raise
    finally:
        latency_ms = int((time.time() - start) * 1000)
        _log(task_type, model_used, latency_ms, status)
