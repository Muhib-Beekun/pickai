from __future__ import annotations

import os
import subprocess
from pathlib import Path


DEFAULT_TOKEN_FILE = Path(r"C:\Users\Public.DESKTOP-6ORC2C9\Documents\hfCred.txt")


def load_token() -> str | None:
    token = os.getenv("HF_TOKEN")
    if token:
        return token.strip()
    if DEFAULT_TOKEN_FILE.exists():
        return DEFAULT_TOKEN_FILE.read_text(encoding="utf-8").strip()
    return None


def main() -> None:
    repo_id = os.getenv("HF_LORA_REPO", "MuhibBeekun/pickai-qwen2.5-7b-nl-parse-lora")
    source = Path("outputs/lora")
    if not source.exists():
        print("No LoRA output found at outputs/lora; skipping upload")
        return

    token = load_token()
    if not token:
        print("No HF token found; skipping upload")
        return

    env = os.environ.copy()
    env["HF_TOKEN"] = token
    cmd = [
        "hf",
        "upload",
        repo_id,
        str(source),
        ".",
        "--commit-message",
        "PickAI LoRA adapter",
    ]
    subprocess.run(cmd, check=True, env=env)
    print(f"Uploaded LoRA adapter to {repo_id}")


if __name__ == "__main__":
    main()
