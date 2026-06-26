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
EVAL_DOC = PROJECT_ROOT / "docs" / "fine-tune-eval.md"
LOCAL_LORA_DIR = PROJECT_ROOT / "outputs" / "lora"
DEFAULT_BASE_MODEL = os.getenv("PICKAI_BASE_MODEL", "qwen2.5:7b-instruct")
DEFAULT_LORA_MODEL = os.getenv("PICKAI_LORA_MODEL", "pickai-qwen2.5-lora")

os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")


_LOCAL_LORA_GENERATOR: tuple[object, object] | None = None


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _prompt(instruction: str, wave_input: dict) -> str:
    return (
        "Return JSON only with key `constraints` containing: equipment_mode, ladder_must_stay_in_aisle, "
        "start_position{aisle,level,x,y}.\n"
        f"Instruction: {instruction}\n"
        f"Wave summary: {json.dumps(wave_input)}"
    )


def _ollama_parse(instruction: str, wave_input: dict, model: str) -> dict:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    payload = {"model": model, "prompt": _prompt(instruction, wave_input), "stream": False}
    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{base_url}/api/generate", json=payload)
        resp.raise_for_status()
        content = resp.json().get("response", "")
    parsed = _extract_json(content)
    return parsed.get("constraints", {}) if isinstance(parsed, dict) else {}


def _load_local_lora() -> tuple[object, object]:
    global _LOCAL_LORA_GENERATOR
    if _LOCAL_LORA_GENERATOR is not None:
        return _LOCAL_LORA_GENERATOR

    import torch
    from peft import AutoPeftModelForCausalLM
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(LOCAL_LORA_DIR), trust_remote_code=True)
    model = AutoPeftModelForCausalLM.from_pretrained(
        str(LOCAL_LORA_DIR),
        torch_dtype=torch.float16,
        trust_remote_code=True,
        device_map="auto",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    _LOCAL_LORA_GENERATOR = (tokenizer, model)
    return _LOCAL_LORA_GENERATOR


def _local_lora_parse(instruction: str, wave_input: dict) -> dict:
    import torch

    tokenizer, model = _load_local_lora()
    prompt = _prompt(instruction, wave_input)
    encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        output = model.generate(
            **encoded,
            max_new_tokens=160,
            do_sample=False,
            temperature=None,
            pad_token_id=tokenizer.eos_token_id,
        )
    completion = tokenizer.decode(output[0][encoded["input_ids"].shape[1] :], skip_special_tokens=True)
    parsed = _extract_json(completion)
    return parsed.get("constraints", {}) if isinstance(parsed, dict) else {}


def _normalize_constraints(c: dict) -> dict:
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


def _score(pred: dict, truth: dict) -> dict:
    p = _normalize_constraints(pred)
    t = _normalize_constraints(truth)

    equipment = 1.0 if p["equipment_mode"] == t["equipment_mode"] else 0.0
    ladder = 1.0 if p["ladder_must_stay_in_aisle"] == t["ladder_must_stay_in_aisle"] else 0.0
    position = 1.0 if (
        p["start_position"]["aisle"] == t["start_position"]["aisle"]
        and p["start_position"]["level"] == t["start_position"]["level"]
        and abs(p["start_position"]["x"] - t["start_position"]["x"]) < 1e-6
        and abs(p["start_position"]["y"] - t["start_position"]["y"]) < 1e-6
    ) else 0.0

    aggregate = (equipment + ladder + position) / 3.0
    return {
        "aggregate": aggregate,
        "equipment_mode": equipment,
        "ladder_position": position,
        "aisle_constraint": ladder,
        "wave_params": 1.0,
    }


def _evaluate(rows: list[dict], model: str, parser) -> dict:
    totals = {"aggregate": 0.0, "equipment_mode": 0.0, "ladder_position": 0.0, "aisle_constraint": 0.0, "wave_params": 0.0}
    count = 0

    for idx, row in enumerate(rows):
        instruction = row["instruction"]
        wave_input = row["input"]
        truth = row["output"]["constraints"]
        pred = parser(instruction, wave_input)
        score = _score(pred, truth)
        for key in totals:
            totals[key] += score[key]
        count += 1

        if (idx + 1) % 10 == 0:
            print(f"{model}: processed {idx + 1}/{len(rows)}", flush=True)

    if count == 0:
        return {k: 0.0 for k in totals}
    return {k: totals[k] / count for k in totals}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--phase", type=str, default="before-training", choices=["before-training", "after-training"])
    args = parser.parse_args()

    if not SYNTHETIC_PATH.exists():
        raise FileNotFoundError(f"Missing synthetic dataset at {SYNTHETIC_PATH}")

    rows = [json.loads(line) for line in SYNTHETIC_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    holdout = rows[-args.limit :]

    base_scores = _evaluate(holdout, DEFAULT_BASE_MODEL, lambda instruction, wave_input: _ollama_parse(instruction, wave_input, DEFAULT_BASE_MODEL))

    lora_scores = None
    lora_error = None
    try:
        if LOCAL_LORA_DIR.exists():
            lora_scores = _evaluate(holdout, str(LOCAL_LORA_DIR), _local_lora_parse)
        else:
            lora_scores = _evaluate(holdout, DEFAULT_LORA_MODEL, lambda instruction, wave_input: _ollama_parse(instruction, wave_input, DEFAULT_LORA_MODEL))
    except Exception as exc:
        lora_error = f"LoRA eval unavailable: {type(exc).__name__}: {exc}"

    lines = []
    if EVAL_DOC.exists():
        lines = EVAL_DOC.read_text(encoding="utf-8").splitlines()

    section_title = "## Before training" if args.phase == "before-training" else "## After training"
    section = [
        section_title,
        "",
        f"Held-out examples: {len(holdout)}",
        f"Base model: {DEFAULT_BASE_MODEL}",
        f"LoRA model: {str(LOCAL_LORA_DIR) if LOCAL_LORA_DIR.exists() else DEFAULT_LORA_MODEL}",
        "",
        "| Metric | Base | LoRA |",
        "|---|---:|---:|",
        f"| Aggregate field match | {base_scores['aggregate']*100:.2f}% | {(lora_scores['aggregate']*100 if lora_scores else 0):.2f}% |",
        f"| Equipment mode | {base_scores['equipment_mode']*100:.2f}% | {(lora_scores['equipment_mode']*100 if lora_scores else 0):.2f}% |",
        f"| Ladder position | {base_scores['ladder_position']*100:.2f}% | {(lora_scores['ladder_position']*100 if lora_scores else 0):.2f}% |",
        f"| Aisle constraint | {base_scores['aisle_constraint']*100:.2f}% | {(lora_scores['aisle_constraint']*100 if lora_scores else 0):.2f}% |",
        "",
    ]
    if lora_error:
        section.append(f"LoRA note: {lora_error}")
        section.append("")

    if lines and section_title in "\n".join(lines):
        text = "\n".join(lines)
        pattern = re.compile(re.escape(section_title) + r".*?(?=\n## |\Z)", re.DOTALL)
        updated = pattern.sub(lambda _: "\n".join(section), text)
        EVAL_DOC.write_text(updated.strip() + "\n", encoding="utf-8")
    else:
        header = ["# Fine-tune Evaluation", "", "Real model-call evaluation using Ollama parsing against held-out synthetic ground truth.", ""]
        existing = lines if lines else header
        EVAL_DOC.write_text("\n".join(existing + section) + "\n", encoding="utf-8")

    print(json.dumps({"phase": args.phase, "base": base_scores, "lora": lora_scores, "lora_note": lora_error}, indent=2))


if __name__ == "__main__":
    main()
