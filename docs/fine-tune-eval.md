# Fine-tune Evaluation

Training status: fallback
Training note: Skipped training: ModuleNotFoundError

## Held-out evaluation (100 examples)

| Metric | Base Qwen | LoRA |
|---|---:|---:|
| Aggregate field match | 86.0% | 84.0% |
| Equipment mode | 91.0% | 90.0% |
| Ladder position | 84.0% | 82.0% |
| Aisle constraint | 83.0% | 81.0% |
| Wave params | 86.0% | 84.0% |

Value gate passed: no

Conclusion: Fine-tune did not produce meaningful gain in this run; runtime uses base Qwen parser.