# Samples Quickstart

1. Run `docker compose up` from project root.
2. Open Streamlit and upload `samples/order_lines_minimal.csv`.
3. Or call API with `samples/expected_optimize_request.json`:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/waves/optimize" -Headers @{"X-API-Key"="dev"} -ContentType "application/json" -Body (Get-Content samples/expected_optimize_request.json -Raw)
```

Files:
- `order_lines_minimal.csv`: quickest smoke run.
- `order_lines_with_aisles.csv`: includes aisle and level data.
- `location_master.csv`: reference location table shape.
- `expected_optimize_request.json`: API equivalent payload.
