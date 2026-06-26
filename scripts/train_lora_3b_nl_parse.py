"""Train LoRA on Qwen2.5-3B for NL constraint parsing (smaller deployable model)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

env = os.environ.copy()
env["PICKAI_TRAIN_BASE_MODEL"] = "Qwen/Qwen2.5-3B-Instruct"
env["PICKAI_LORA_OUT_DIR"] = str(PROJECT_ROOT / "outputs" / "lora-3b")
env["PICKAI_MAX_STEPS"] = env.get("PICKAI_MAX_STEPS", "400")
env["PICKAI_LORA_RANK"] = env.get("PICKAI_LORA_RANK", "32")
env.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
env.setdefault("CUDA_VISIBLE_DEVICES", "0")

subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "train_lora_nl_parse.py")], env=env, check=True)
