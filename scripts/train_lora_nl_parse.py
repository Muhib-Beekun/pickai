from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pickai.inference.dataset_split import split_holdout
from pickai.inference.nl_parse_prompt import build_nl_parse_completion, build_nl_parse_prompt

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

SYNTHETIC = PROJECT_ROOT / "data" / "synthetic" / "synthetic_nl_parse.jsonl"
REFINED = PROJECT_ROOT / "data" / "synthetic" / "refined_nl_parse.jsonl"
HOLDOUT_PATH = PROJECT_ROOT / "data" / "synthetic" / "holdout_nl_parse.jsonl"
OUT_DIR = PROJECT_ROOT / "outputs" / "lora"
LOG_FILE = PROJECT_ROOT / "outputs" / "lora_train_log.json"
BASE_MODEL = os.getenv("PICKAI_TRAIN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
HOLDOUT_N = int(os.getenv("PICKAI_HOLDOUT_N", "100"))


def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _training_text(row: dict) -> str:
    prompt = build_nl_parse_prompt(row["instruction"], row["input"])
    completion = build_nl_parse_completion(row["output"]["constraints"])
    return prompt + completion


def main() -> None:
    synthetic_rows = _read_rows(SYNTHETIC)
    refined_rows = _read_rows(REFINED)
    if not synthetic_rows:
        raise RuntimeError("No synthetic rows found. Run scripts/generate_synthetic_jsonl.py first.")

    train_synthetic, holdout = split_holdout(synthetic_rows, holdout_n=HOLDOUT_N)
    train_rows = train_synthetic + refined_rows

    HOLDOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HOLDOUT_PATH.write_text("\n".join(json.dumps(row) for row in holdout) + "\n", encoding="utf-8")

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
    except Exception as exc:
        raise RuntimeError(f"Missing training dependencies: {exc}")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; cannot run 3090 LoRA training")

    device_name = torch.cuda.get_device_name(0)
    if "3090" not in device_name:
        raise RuntimeError(f"GPU policy violation: expected RTX 3090, found {device_name}")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize_row(row: dict) -> dict:
        prompt = build_nl_parse_prompt(row["instruction"], row["input"])
        completion = build_nl_parse_completion(row["output"]["constraints"])
        full = prompt + completion
        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        encoded = tokenizer(full, truncation=True, max_length=1024, padding="max_length")
        labels = encoded["input_ids"].copy()
        prompt_token_count = min(len(prompt_ids), len(labels))
        for idx in range(prompt_token_count):
            labels[idx] = -100
        if encoded["attention_mask"][-1] == 0:
            for idx, mask in enumerate(encoded["attention_mask"]):
                if mask == 0:
                    labels[idx] = -100
        encoded["labels"] = labels
        return encoded

    tokenized_rows = [tokenize_row(row) for row in train_rows]
    dataset = Dataset.from_dict(
        {
            "input_ids": [row["input_ids"] for row in tokenized_rows],
            "attention_mask": [row["attention_mask"] for row in tokenized_rows],
            "labels": [row["labels"] for row in tokenized_rows],
        }
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        trust_remote_code=True,
        device_map="auto",
    )
    model.config.use_cache = False

    lora_config = LoraConfig(
        r=int(os.getenv("PICKAI_LORA_RANK", "16")),
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    args = TrainingArguments(
        output_dir=str(OUT_DIR),
        num_train_epochs=1,
        max_steps=int(os.getenv("PICKAI_MAX_STEPS", "150")),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        report_to=[],
    )

    trainer = Trainer(model=model, args=args, train_dataset=dataset)

    status = "success"
    note = ""
    try:
        trainer.train()
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower():
            status = "oom"
            note = "OOM encountered; recommended fallback: batch=1, rank=8, max_steps=300"
        else:
            status = "failed"
            note = str(exc)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if status == "success":
        model.save_pretrained(str(OUT_DIR))
        tokenizer.save_pretrained(str(OUT_DIR))

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(
        json.dumps(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "status": status,
                "note": note,
                "base_model": BASE_MODEL,
                "train_rows": len(train_rows),
                "holdout_rows": len(holdout),
                "refined_rows": len(refined_rows),
                "prompt_format": "eval_aligned",
                "gpu": device_name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if status != "success":
        raise RuntimeError(f"Training did not complete: {status} - {note}")

    print(f"LoRA adapter saved to {OUT_DIR} ({len(train_rows)} train rows, {len(holdout)} holdout excluded)")


if __name__ == "__main__":
    main()
