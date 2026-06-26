# Facility Console

Map-centric setup and operations for PickAI. Not a WMS — a WMS-adjacent optimization layer.

## Modes

### Setup
- Edit `FacilityProfile`: locations, aisle rules (one-way, blocked), zones, resource pool
- BYOK inference: Ollama (default), OpenAI, Anthropic, Azure, custom base URL
- NL chat parses supervisor constraints via the same prompt as eval (`nl_parse_prompt.py`)
- Publish increments `version` for audit and WMS integration

### Operations
- `POST /v1/tasks/optimize` with pick and put task lines
- Multi-picker zone split with aisle conflict warnings
- Heat layers: pick density, walk burden, congestion
- Route preview on the facility map

### Scenario compare
- Compare published profile vs draft (e.g. more pickers) on the same sample wave

## Storage

```
data/facilities/{tenant_id}/{facility_id}.json
```

Default: `default/main.json` seeded from `samples/location_master.csv` and `data/fixtures/aisle_rules.json`.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /v1/facility/profile` | Load profile |
| `PUT /v1/facility/profile?publish=true` | Save or publish |
| `GET /v1/facility/profile/export?format=geojson` | WMS integration export |
| `POST /v1/tasks/optimize` | Pick + put multi-resource optimize |
| `POST /v1/waves/optimize` | Legacy WMS wave alias |

## Docker

```powershell
docker compose up -d --build
```

- API: `:8000`
- Facility Console: `:8502`
- Legacy lab: `:8501`
