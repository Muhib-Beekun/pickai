# Architecture

## Baseline

The upstream `picking-route` project is a Streamlit application focused on warehouse picking-route simulation.

- Entrypoint: `app.py`
- Routing utilities: `utils/routing/`
- Batching utilities: `utils/batch/`
- Clustering utilities: `utils/cluster/`
- Plotting utilities: `utils/results/`
- Sample input data: `static/in/df_lines.csv`

## PickAI target architecture

PickAI extends the baseline into layered modules:

- Contracts: `pickai/contracts/` (Pydantic models)
- Domain: `pickai/domain/` (optimizer, routing, batching)
- Adapters: `pickai/adapters/` (dataset and WMS import adapters)
- Inference: `pickai/inference/` (LLM gateway)
- API: `pickai/api/` (FastAPI)
- UI: Streamlit in `app.py` and `pickai/ui/`
