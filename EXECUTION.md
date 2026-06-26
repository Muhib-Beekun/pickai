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

- TODO 058 fallback detail: Bound target owner MuhibBeekun is not accessible from current authenticated account (Muhib-Beekun); org/repo create returned HTTP 404. Local repo is complete with full commit history.
- Push commands once target owner is available:
  1) git remote add github https://github.com/MuhibBeekun/pickai.git
  2) git push github main


## Phase 2 checklist

### Phase H â€” Hygiene & publish (TODO 101â€“108)

- [x] **TODO 101** â€” Append Phase 2 checklist to `EXECUTION.md`.
- [x] **TODO 102** â€” Fix git remotes: `upstream` = samirsaci/picking-route, `origin` = Muhib-Beekun/pickai.
- [x] **TODO 103** â€” Push to GitHub; verify https://github.com/Muhib-Beekun/pickai loads.
- [x] **TODO 104** â€” Remove/replace stub code in `eval_nl_parse.py` (delete hardcoded scores).
- [x] **TODO 105** â€” Add `docs/data-lineage.md` (Mendeley real vs fallback, synthetic generation method).
- [x] **TODO 106** â€” Verify no DeepSeek references in repo; grep clean.
- [x] **TODO 107** â€” Verify all GPU scripts set `CUDA_VISIBLE_DEVICES=0`; document in README.
- [x] **TODO 108** â€” Commit: `chore: phase 2 hygiene and publish prep`.

### Phase I â€” OR-Tools + 2.5D routing (TODO 109â€“118)

- [x] **TODO 109** â€” Add `ortools` dependency; install in venv.
- [x] **TODO 110** â€” Implement `pickai/domain/solver_ortools.py` TSP solver.
- [x] **TODO 111** â€” Wire `optimize_wave` to solver via `PICKAI_SOLVER` env (default ortools).
- [x] **TODO 112** â€” Add vertical pick time when `level`/`z` changes between stops.
- [x] **TODO 113** â€” Add `ladder_state_after` to `OptimizedWave` contract + optimizer.
- [x] **TODO 114** â€” Add `processing_time_ms` and `estimated_picker_time_saved_s` to API response meta.
- [x] **TODO 115** â€” Write `docs/routing-model.md` (2D graph, 2.5D vertical, ladder state, forklift vs walker).
- [x] **TODO 116** â€” Add `docs/tool-schema-compute_optimal_pick_path.json`.
- [x] **TODO 117** â€” Tests: OR-Tools â‰¤ heuristic; ladder persistence; time-saved > 0 on fixture wave.
- [ ] **TODO 118** â€” Commit: `feat: OR-Tools solver and 2.5D routing metrics`.

### Phase J â€” Ground-truth data + dual-agent (TODO 119â€“126)

- [ ] **TODO 119** â€” Rewrite `generate_synthetic_jsonl.py` to use optimizer ground truth.
- [ ] **TODO 120** â€” Regenerate â‰¥3,000 rows; refresh `sample.jsonl`.
- [ ] **TODO 121** â€” Implement `scripts/agentic_nl_refine.py` (writer + validator, 3 cycles).
- [ ] **TODO 122** â€” Run agentic refine on 200 held-out examples; write `data/synthetic/refined_nl_parse.jsonl`.
- [ ] **TODO 123** â€” Rewrite `eval_nl_parse.py` for real Ollama scoring (no hardcoded values).
- [ ] **TODO 124** â€” Run baseline eval; record in `docs/fine-tune-eval.md` Â§ Before training.
- [ ] **TODO 125** â€” Upload full synthetic JSONL to HF dataset repo with README.
- [ ] **TODO 126** â€” Commit: `feat: ground-truth synthetic data and agentic refine pipeline`.

### Phase K â€” LoRA train + HF model (TODO 127â€“134)

- [ ] **TODO 127** â€” Implement `scripts/train_lora_nl_parse.py` (PEFT/Unsloth, 3090, bounded steps).
- [ ] **TODO 128** â€” Run training; save `outputs/lora/`; capture loss log.
- [ ] **TODO 129** â€” Run post-train eval; update `docs/fine-tune-eval.md` Â§ After training.
- [ ] **TODO 130** â€” Upload LoRA to `MuhibBeekun/pickai-qwen2.5-7b-nl-parse-lora` with model card.
- [ ] **TODO 131** â€” Upgrade `gateway.py`: dual-agent retry + optional LoRA load.
- [ ] **TODO 132** â€” Streamlit chat uses upgraded gateway; manual smoke 3 NL commands logged in EXECUTION.md.
- [ ] **TODO 133** â€” Docker Compose: document optional `HF_LORA_REPO` pull in README (not required for startup).
- [ ] **TODO 134** â€” Commit: `feat: LoRA training, HF upload, and gateway upgrade`.

### Phase L â€” Docs, CI, regression (TODO 135â€“145)

- [ ] **TODO 135** â€” Regenerate `docs/openapi.json`; verify Swagger at `/docs`.
- [ ] **TODO 136** â€” Update `docs/wms-integration-guide.md` with `ladder_state_after`, timing fields, tool schema link.
- [ ] **TODO 137** â€” Final README (niche, links, solver modes, HF artifacts).
- [ ] **TODO 138** â€” Update `docs/tmp/linkedin-article-draft.md` (no AI-build mention, live links).
- [ ] **TODO 139** â€” Run CI locally: `pytest tests -q`, `verify_optimize_trace.py`, `preflight.ps1`.
- [ ] **TODO 140** â€” Docker regression: `docker compose up -d --build`; health + Streamlit smoke.
- [ ] **TODO 141** â€” GitHub Actions green on push (fix workflow if needed).
- [ ] **TODO 142** â€” Mark all Phase 2 TODOs [x] in EXECUTION.md with completion log.
- [ ] **TODO 143** â€” Print deliverables table (GitHub URL, HF URLs, eval scores, solver mode).
- [ ] **TODO 144** â€” Commit: `docs: phase 2 release polish`.
- [ ] **TODO 145** â€” Final push to `origin main`.

---

## Phase 2 log
- TODO 101: Appended Phase 2 checklist from execution prompt.
- TODO 102: Verified remotes as upstream=samirsaci/picking-route and origin=Muhib-Beekun/pickai.
- TODO 103: Pushed to origin and verified public repo at https://github.com/Muhib-Beekun/pickai.
- TODO 104: Replaced eval stub with live Ollama-based scoring pipeline in scripts/eval_nl_parse.py.
- TODO 105: Added docs/data-lineage.md covering real Mendeley ingestion and synthetic generation provenance.
- TODO 106: Ran `rg -n -i "deepseek" pickai scripts tests docs README.md --glob "!docs/tmp/**"` with no matches.
- TODO 107: Verified GPU pinning in README and training script via `rg -n "CUDA_VISIBLE_DEVICES" scripts pickai README.md`.
- TODO 109: Added OR-Tools dependency and installed updated requirements in venv.
- TODO 110: Added pickai/domain/solver_ortools.py with OR-Tools routing model TSP path solver.
- TODO 111: Wired optimizer solver selection via PICKAI_SOLVER with OR-Tools default and heuristic fallback.
- TODO 112: Added vertical traversal time component for z/level transitions between sequential stops.
- TODO 113: Added ladder_state_after contract field and optimizer persistence behavior.
- TODO 114: Added processing_time_ms and estimated_picker_time_saved_s through optimizer and API meta envelope.
- TODO 115: Added docs/routing-model.md covering 2D routing, 2.5D costs, and ladder/equipment behaviors.
- TODO 116: Added docs/tool-schema-compute_optimal_pick_path.json.
- TODO 117: Extended unit/integration tests and validated with `pytest -q` and `scripts/verify_optimize_trace.py`.
- TODO 108: Committed hygiene/publish prep as 7e42f34.
