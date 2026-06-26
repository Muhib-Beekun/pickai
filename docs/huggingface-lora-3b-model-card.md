---
license: mit
base_model: Qwen/Qwen2.5-3B-Instruct
tags:
  - warehouse
  - pick-path
  - lora
  - structured-output
---

# PickAI Qwen2.5-3B NL Parse LoRA (experimental)

Smaller deployable adapter for PickAI supervisor constraint parsing. Trained with eval-aligned prompts (`pickai/inference/nl_parse_prompt.py`) on [pickai-synthetic-nl-parse-v1](https://huggingface.co/datasets/MuhibBeekun/pickai-synthetic-nl-parse-v1).

## Use

```python
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("MuhibBeekun/pickai-qwen2.5-3b-nl-parse-lora")
model = AutoPeftModelForCausalLM.from_pretrained("MuhibBeekun/pickai-qwen2.5-3b-nl-parse-lora")
```

Local path: `outputs/lora-3b` with `PICKAI_USE_LORA=1` and `PICKAI_LOCAL_LORA_DIR=outputs/lora-3b`.

## Training

```powershell
python scripts/train_lora_3b_nl_parse.py
python scripts/eval_nl_parse.py --lora-dir outputs/lora-3b --phase 3b-pass
```

See [fine-tune-eval.md](https://github.com/Muhib-Beekun/pickai/blob/main/docs/fine-tune-eval.md) for value-gate results.

## License

MIT. PickAI extends [samirsaci/picking-route](https://github.com/samirsaci/picking-route).
