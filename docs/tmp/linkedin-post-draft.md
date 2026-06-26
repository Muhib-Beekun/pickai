# LinkedIn Launch Draft

I just open-sourced PickAI: a warehouse pick-path optimizer built for practical WMS integration.

What it does:
- Optimizes pick routes from wave order lines
- Supports ladder-aware and equipment-aware routing
- Exposes a FastAPI `/v1` interface for integration teams
- Includes a Streamlit console and ready-to-run sample files

Why I built it:
- To move from simulation-only notebooks toward integration-ready tooling
- To make route optimization reproducible for operations teams
- To keep the release practical: Docker-first, documented, MIT licensed

Tech stack:
- Python, FastAPI, Streamlit, Plotly, Pydantic
- Optional Ollama-based local NL parsing
- Inspired by and attributed to Samir Saci’s original picking-route work

If you work in warehousing, logistics engineering, or WMS integrations, I’d love feedback.

Repo: https://github.com/MuhibBeekun/pickai
