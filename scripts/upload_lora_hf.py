"""Upload LoRA adapter and README to Hugging Face."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REPO_ID = os.getenv("PICKAI_HF_LORA_REPO", "MuhibBeekun/pickai-qwen2.5-3b-nl-parse-lora")
LORA_DIR = Path(os.getenv("PICKAI_LORA_OUT_DIR", str(PROJECT_ROOT / "outputs" / "lora-3b")))
MODEL_CARD = PROJECT_ROOT / "docs" / "huggingface-lora-3b-model-card.md"


def main() -> None:
    if not LORA_DIR.exists():
        raise FileNotFoundError(f"LoRA dir missing: {LORA_DIR}")

    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise RuntimeError("pip install huggingface_hub") from exc

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not token:
        raise RuntimeError("Set HF_TOKEN or HUGGING_FACE_HUB_TOKEN")

    api = HfApi(token=token)
    api.create_repo(repo_id=REPO_ID, repo_type="model", exist_ok=True)
    api.upload_folder(folder_path=str(LORA_DIR), repo_id=REPO_ID, repo_type="model")
    if MODEL_CARD.exists():
        api.upload_file(
            path_or_fileobj=str(MODEL_CARD),
            path_in_repo="README.md",
            repo_id=REPO_ID,
            repo_type="model",
        )
    print(f"Uploaded {LORA_DIR} to https://huggingface.co/{REPO_ID}")


if __name__ == "__main__":
    main()
