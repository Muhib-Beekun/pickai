# Fine-tune Evaluation

Real model-call evaluation using Ollama parsing against held-out synthetic ground truth.

## Before training

Held-out examples: 100  
Base model: qwen2.5:7b-instruct via Ollama

- Aggregate field match: 98.67%
- Equipment mode: 96.00%
- Ladder position: 100.00%
- Aisle constraint: 100.00%

## After training

Held-out examples: 100  
Base model: qwen2.5:7b-instruct via Ollama  
LoRA adapter: `outputs/lora` (PEFT, trained on RTX 3090)

- Aggregate field match — base 99.33%, LoRA 17.67%
- Equipment mode — base 98.00%, LoRA 0.00%
- Ladder position — base 100.00%, LoRA 0.00%
- Aisle constraint — base 100.00%, LoRA 53.00%

Value gate passed: no

Conclusion: the trained LoRA adapter regressed sharply versus the base Qwen runtime on the held-out set. Release runtime should remain on the base Ollama model unless a later adapter exceeds the baseline.

Optional local adapter path: set `PICKAI_USE_LORA=1` and keep `outputs/lora` available. Default Docker and Streamlit flows do not require it.

## Parity pass (prompt-aligned holdout)

Held-out examples: 100 (deterministic hash split, not tail rows)
Prompt format: eval-aligned (`pickai/inference/nl_parse_prompt.py`)
Base model: qwen2.5:7b-instruct
LoRA adapter: `outputs/lora`

| Metric | Base | LoRA |
|---|---:|---:|
| Aggregate field match | 100.00% | 44.67% |
| Equipment mode | 100.00% | 28.00% |
| Ladder position | 100.00% | 28.00% |
| Aisle constraint | 100.00% | 78.00% |

Training: 2,966 rows, eval-aligned prompt, label masking, 150 steps on RTX 3090. LoRA improved versus the misaligned first run (17.67% aggregate) but still regressed versus base.

## Value gate

Value gate passed: no

## Conclusion

Release runtime remains on base `qwen2.5:7b-instruct` via Ollama. Prompt parity and a hash holdout were required for a fair experiment; they were not sufficient to beat base on synthetic NL.
