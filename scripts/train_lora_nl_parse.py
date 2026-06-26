from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

SYNTHETIC = PROJECT_ROOT / "data" / "synthetic" / "synthetic_nl_parse.jsonl"
REFINED = PROJECT_ROOT / "data" / "synthetic" / "refined_nl_parse.jsonl"
OUT_DIR = PROJECT_ROOT / "outputs" / "lora"
LOG_FILE = PROJECT_ROOT / "outputs" / "lora_train_log.json"
BASE_MODEL = os.getenv("PICKAI_TRAIN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")


def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _to_text_example(row: dict) -> str:
    return (
        "Instruction:\n"
        + row["instruction"]
        + "\n\nInput:\n"
        + json.dumps(row["input"])
        + "\n\nOutput:\n"
        + json.dumps(row["output"]["constraints"])
    )


def main() -> None:
    rows = _read_rows(SYNTHETIC)
    rows += _read_rows(REFINED)
    if not rows:
        raise RuntimeError("No training rows found. Generate synthetic and refine datasets first.")

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

    dataset = Dataset.from_dict({"text": [_to_text_example(row) for row in rows]})

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

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

    def tokenize(batch):
        enc = tokenizer(batch["text"], truncation=True, max_length=1024, padding="max_length")
        enc["labels"] = enc["input_ids"].copy()
        return enc

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])

    args = TrainingArguments(
        output_dir=str(OUT_DIR),
        num_train_epochs=1,
        max_steps=int(os.getenv("PICKAI_MAX_STEPS", "800")),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        report_to=[],
    )

    trainer = Trainer(model=model, args=args, train_dataset=tokenized)

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
                "rows": len(rows),
                "gpu": device_name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if status != "success":
        raise RuntimeError(f"Training did not complete: {status} - {note}")

    print(f"LoRA adapter saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
