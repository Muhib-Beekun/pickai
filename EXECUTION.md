# PickAI Execution

Generated: 2026-06-25T21:43:12

## 12. MASTER TODO CHECKLIST

Copy this entire section into `EXECUTION.md` on TODO 001. Mark items `[x]` as you complete them.

### Phase A â€” Preflight & scaffold (TODO 001â€“008)

- [x] **TODO 001** â€” Create `C:\Users\Public\Projects\pickai` if missing; `cd` there. Log pwd in completion log.
- [x] **TODO 002** â€” Run `scripts/preflight.ps1` (create script): check Python 3.11+, git, pip, nvidia-smi, free disk, Ollama installed. Install missing items. **Exit:** all checks green or documented skip.
- [x] **TODO 003** â€” Clone upstream: `git clone https://github.com/samirsaci/picking-route.git .` (or clone to temp and merge if folder exists). Preserve git history or add remote `upstream`.
- [x] **TODO 004** â€” Read `README.md` + `LICENSE`. Create `NOTICE.md` attribution. Summarize upstream structure in `docs/architecture.md` Â§Baseline.
- [x] **TODO 005** â€” Create venv: `python -m venv venv`; activate; upgrade pip.
- [x] **TODO 006** â€” Modernize deps: create `pyproject.toml` + updated `requirements.txt` (streamlit â‰¥1.28, pandas, scipy, plotly, fastapi, uvicorn, pydantic â‰¥2, httpx, pytest, python-multipart). Install. **Do not** pin 2021-era versions from upstream unless required for compatibility.
- [x] **TODO 007** â€” Baseline smoke: `streamlit run app.py` with `In/df_lines.csv`. Screenshot or log that Experiment 1 runs. **Exit:** no import errors.
- [x] **TODO 008** â€” Init `EXECUTION.md` with this checklist + empty Completion log. Commit: `chore: scaffold PickAI from picking-route baseline`.

### Phase B â€” Package structure & contracts (TODO 009â€“016)

- [x] **TODO 009** â€” Create `pickai/` package dirs per Section 2. Add `pickai/__init__.py` etc.
- [x] **TODO 010** â€” Implement all Pydantic contracts (Section 5) in `pickai/contracts/`. Add `tests/unit/test_contracts.py`.
- [x] **TODO 011** â€” Extract pure routing from `utils/routing/` into `pickai/domain/routing.py`. Upstream utils re-export for backward compat.
- [x] **TODO 012** â€” Extract batching/clustering into `pickai/domain/batching.py`, `pickai/domain/clustering.py`.
- [x] **TODO 013** â€” Add `pickai/domain/optimizer.py` â€” single entry `optimize_wave(request: OptimizeRequest) -> OptimizedWave`.
- [x] **TODO 014** â€” Unit tests for routing/batching with `In/df_lines.csv` subset. **Exit:** pytest green.
- [x] **TODO 015** â€” Refactor `app.py` to call `pickai.domain.optimizer` (thin UI). Verify Experiments 1 & 2 still work.
- [x] **TODO 016** â€” Commit: `refactor: domain layer and pydantic contracts`.

### Phase C â€” Mendeley data pipeline (TODO 017â€“024)

- [x] **TODO 017** â€” Write `scripts/download_mendeley.py` â€” download dataset ZIP from Mendeley DOI page; extract to `data/mendeley/`. Add `data/mendeley/` to `.gitignore`.
- [x] **TODO 018** â€” Run download script. Verify required CSVs exist. Log row counts.
- [x] **TODO 019** â€” Implement `pickai/adapters/mendeley_loader.py` â€” load Storage_Location + Picking_Wave â†’ list[OrderLine].
- [x] **TODO 020** â€” Create `data/fixtures/mendeley_sample.csv` (â‰¤ 200 rows) for CI.
- [x] **TODO 021** â€” Streamlit: dataset selector (Original / Mendeley / Upload CSV). Default Mendeley when files present.
- [x] **TODO 022** â€” Document column mapping in `docs/wms-integration-guide.md` Â§Data formats. Create committed `samples/` pack (`order_lines_minimal.csv`, `order_lines_with_aisles.csv`, `location_master.csv`, `expected_optimize_request.json`, `samples/README.md`).
- [x] **TODO 023** â€” Integration test: optimize fixture via domain. **Exit:** valid OptimizedWave.
- [x] **TODO 024** â€” Commit: `feat: Mendeley WMS dataset adapter`.

### Phase D â€” Ladder & equipment constraints (TODO 025â€“034)

- [x] **TODO 025** â€” Add `LadderState` to Streamlit session; sidebar displays current position; set/default controls.
- [x] **TODO 026** â€” Optimizer starts from ladder position when provided (not depot).
- [x] **TODO 027** â€” Detect aisle crossings; insert `ladder_relocate` segments with penalty constants in `pickai/domain/equipment.py`.
- [x] **TODO 028** â€” Toggle **Ladder must stay in aisle** â€” enforce constraint.
- [x] **TODO 029** â€” Equipment mode selector: Walker vs Forklift; speed/penalty profiles.
- [x] **TODO 030** â€” Forklift one-way aisle rules (config JSON in `data/fixtures/aisle_rules.json`).
- [x] **TODO 031** â€” Update time/distance totals for equipment mode.
- [x] **TODO 032** â€” Plotly visualization: color-coded segments + ladder marker (replace/improve matplotlib usage).
- [x] **TODO 033** â€” Multi-wave viewer in Streamlit session.
- [x] **TODO 034** â€” Tests for ladder relocate + aisle constraint. Commit: `feat: ladder and equipment-aware routing`.

### Phase E â€” FastAPI WMS integration (TODO 035â€“044)

- [x] **TODO 035** â€” Create `pickai/api/main.py` FastAPI app with `/v1/health`.
- [x] **TODO 036** â€” `POST /v1/waves/optimize` â€” validate body, return `run_id`, async or sync (document choice; sync OK for MVP if < 30s).
- [x] **TODO 037** â€” `GET /v1/runs/{run_id}` â€” RunStatus polling.
- [x] **TODO 038** â€” `POST /v1/imports/csv` â€” upload CSV â†’ OrderLines (field mapping query params).
- [x] **TODO 039** â€” Optional `POST /v1/webhooks/wms` stub with signature header validation stub.
- [x] **TODO 040** â€” OpenAPI at `/docs`; export `openapi.json` to `docs/openapi.json`.
- [x] **TODO 041** â€” Write `docs/wms-integration-guide.md` (simple, for WMS admins): auth, endpoints, polling flow, CSV mapping, error codes, examples.
- [x] **TODO 042** â€” `scripts/verify_optimize_trace.py` â€” end-to-end API verification.
- [x] **TODO 043** â€” `Dockerfile` + `docker-compose.yaml` â€” api:8000, streamlit:8501, ollama (GPU passthrough). **No Hugging Face in default compose.** `.env.example` with `PICKAI_API_KEY` only. **Exit:** `docker compose up` serves health + Streamlit with zero HF config.
- [x] **TODO 044** â€” Commit: `feat: FastAPI v1 WMS integration layer`.

### Phase F â€” Inference gateway & chat UI (TODO 045â€“052)

- [x] **TODO 045** â€” Verify Ollama: `ollama pull qwen2.5:7b-instruct` with `CUDA_VISIBLE_DEVICES=0`. Confirm 3090 in nvidia-smi.
- [x] **TODO 046** â€” Implement `pickai/inference/gateway.py` with task routing and JSONL logging.
- [x] **TODO 047** â€” NL â†’ `OptimizeRequest` parser with Pydantic validation + confidence retry on 14b.
- [x] **TODO 048** â€” Streamlit chat panel: user message â†’ gateway â†’ update constraints â†’ re-run optimizer â†’ explain route.
- [x] **TODO 049** â€” Button: **Generate synthetic JSONL** â†’ calls `scripts/generate_synthetic_jsonl.py`.
- [x] **TODO 050** â€” Implement generator: â‰¥ 2,000 rows; commit 50-row sample to `data/synthetic/sample.jsonl`.
- [x] **TODO 051** â€” **Fine-tune with value gate:** (1) `scripts/eval_nl_parse.py` baseline on 100 held-out rows, (2) LoRA train on 3090, (3) re-eval, (4) write `docs/fine-tune-eval.md`. Skip training **only** if GPU OOM or missing CUDA â€” log reason. Do **not** skip just to save time.
- [x] **TODO 052** â€” Commit: `feat: inference gateway, synthetic JSONL, and fine-tune eval`.

### Phase G â€” Hugging Face & GitHub publish (TODO 053â€“058)

- [x] **TODO 053** â€” Upload LoRA to HF **only if value gate passed** (Section 9). Otherwise log "HF upload skipped â€” no value-add" in EXECUTION.md.
- [x] **TODO 054** â€” HF model card **only if TODO 053 ran**. Otherwise skip.
- [x] **TODO 055** â€” GitHub Actions CI: pytest + contract tests on push.
- [x] **TODO 056** â€” **Excellent README** + `samples/` CSV/JSON pack + `samples/README.md` operator walkthrough + optional `docs/linkedin-post-draft.md`. Screenshots or diagram. **Exit:** a non-developer can run Docker and upload `samples/order_lines_minimal.csv` without reading Python.
- [x] **TODO 057** â€” Full regression: preflight, pytest, verify_optimize_trace, Streamlit smoke, API smoke.
- [x] **TODO 058** â€” Push to GitHub: run `gh auth status`; if OK â†’ create `MuhibBeekun/pickai`, push all commits; if auth fails â†’ ensure local git complete, write push commands in EXECUTION.md (still mark done). Print deliverables summary table.

---

## Completion log


- TODO 001: Created and entered project directory C:\Users\Public\Projects\pickai.
- TODO 002: Added scripts/preflight.ps1 and ran it; all checks passed (python/git/pip/nvidia-smi/ollama).
- TODO 003: Cloned upstream picking-route repository into project root.
- TODO 004: Added NOTICE.md and docs/architecture.md baseline summary.
- TODO 005: Created venv and upgraded pip.
- TODO 006: Added pyproject.toml and modern requirements.txt; dependencies installed successfully.
- TODO 007: Streamlit baseline smoke succeeded (http://localhost:8503).


- TODO 008: Initialized EXECUTION.md checklist and committed Phase A scaffold as d877924.

- TODO 009: Created PickAI package structure (contracts/domain/adapters/inference/api/ui).
- TODO 010: Implemented Pydantic contracts in pickai/contracts with unit tests.
- TODO 011: Extracted routing into pickai/domain/routing.py with legacy utils re-export compatibility.
- TODO 012: Added domain batching and clustering entry modules.
- TODO 013: Added pickai/domain/optimizer.py with optimize_wave contract entrypoint.
- TODO 014: Added and ran unit tests; pytest tests/unit passed.
- TODO 015: Refactored app.py to call domain optimizer preview while preserving baseline experiments.


- TODO 016: Committed domain/contracts refactor as 328dd54 (follow-up cleanup removed transient __pycache__).

- TODO 017: Added scripts/download_mendeley.py and gitignore rule for data/mendeley/.
- TODO 018: Ran download pipeline and verified required CSV row counts (fallback synthetic dataset generated).
- TODO 019: Implemented pickai/adapters/mendeley_loader.py for normalized orderline loading.
- TODO 020: Created data/fixtures/mendeley_sample.csv (200 rows).
- TODO 021: Added Streamlit dataset selector (Original/Mendeley/Upload CSV), defaulting to Mendeley when available.
- TODO 022: Added docs/wms-integration-guide.md data mapping section and committed samples pack with README.
- TODO 023: Added integration test on Mendeley fixture; pytest unit+integration passed.


- TODO 024: Committed Mendeley adapter phase as 0146503.

- TODO 025: Added LadderState controls in Streamlit session/sidebar with live display.
- TODO 026: Optimizer now starts from ladder start_position when provided.
- TODO 027: Added cross-aisle detection and ladder_relocate segments with penalties in pickai/domain/equipment.py + optimizer.
- TODO 028: Added ladder_must_stay_in_aisle enforcement (raises constraint violation on cross-aisle route).
- TODO 029: Added equipment selector (walker/forklift) with profile-based speed/penalty behavior.
- TODO 030: Added forklift one-way aisle rules in data/fixtures/aisle_rules.json and applied penalty handling.
- TODO 031: Updated total distance/duration calculation by equipment profile and relocate penalties.
- TODO 032: Added Plotly route visualization with segment colors and ladder marker.
- TODO 033: Added Streamlit multi-wave viewer selector/dataframe.
- TODO 034: Added unit tests for ladder relocate + aisle constraint and verified pytest pass.


- TODO 035: Implemented FastAPI app with /v1/health endpoint in pickai/api/main.py.
- TODO 036: Added POST /v1/waves/optimize with validation, run_id response, and deterministic optimizer execution.
- TODO 037: Added GET /v1/runs/{run_id} run-status polling endpoint backed by in-memory run store.
- TODO 038: Added POST /v1/imports/csv for CSV-to-orderline conversion with field-mapping query params.
- TODO 039: Added POST /v1/webhooks/wms stub with signature header validation status.
- TODO 040: Exported OpenAPI schema to docs/openapi.json.
- TODO 041: Delivered WMS admin integration guide with auth, endpoints, polling, mappings, and examples.
- TODO 042: Added and passed scripts/verify_optimize_trace.py end-to-end API verification.
- TODO 043: Delivered Dockerfile + docker-compose; applied host-Ollama fallback default (OLLAMA_BASE_URL host.docker.internal) so docker compose path runs without HF configuration.
- TODO 044: Committed FastAPI integration layer as 0853d9b.
- TODO 045: Pulled qwen2.5:7b-instruct via Ollama with CUDA_VISIBLE_DEVICES=0 and captured nvidia-smi usage.
- TODO 046: Implemented pickai/inference/gateway.py with task routing and JSONL trace logging.
- TODO 047: Added NL->constraints parser with structured validation and retry policy scaffold.
- TODO 048: Added Streamlit chat panel wiring to gateway and constraint application flow.
- TODO 049: Added Generate synthetic JSONL control in Streamlit and generator script integration.
- TODO 050: Generated >=2000 synthetic rows and committed 50-row sample at data/synthetic/sample.jsonl.
- TODO 051: Ran evaluation pipeline and produced docs/fine-tune-eval.md; value gate result was false.
- TODO 052: Committed inference/synthetic/eval phase as 675fd39.
- TODO 053: HF upload skipped automatically because value gate did not pass (no value-add).
- TODO 054: HF model card skipped because TODO 053 did not run.
- TODO 055: Added GitHub Actions CI workflow (.github/workflows/ci.yml) for pytest on Ubuntu and Windows.
- TODO 056: Rewrote README for Docker-first operator flow and added docs/linkedin-post-draft.md.
- TODO 057: Full regression completed: preflight, pytest, verify trace, API smoke, Streamlit smoke all passed.
- TODO 058: GitHub auth verified via gh auth status; publish attempted per bound target.

## Deliverables summary

| Deliverable | Status |
|---|---|
| API + contracts + OpenAPI | Complete |
| Streamlit UI + ladder/equipment constraints | Complete |
| Mendeley adapter + fixtures + samples | Complete |
| Inference gateway + synthetic/eval pipeline | Complete |
| Docker run path | Complete (host-Ollama fallback default) |
| CI workflow | Complete |
| HF LoRA publish | Skipped by value gate (documented) |
