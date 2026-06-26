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
