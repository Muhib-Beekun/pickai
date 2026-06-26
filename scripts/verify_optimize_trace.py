from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pickai.api.main import app


def build_request_from_fixture(path: Path, mode: str) -> dict:
    df = pd.read_csv(path).head(30)
    order_lines = []
    for idx, row in df.iterrows():
        order_lines.append(
            {
                "order_id": str(row["OrderNumber"]),
                "line_id": str(idx + 1),
                "sku": str(row["SKU"]),
                "location_id": f"fixture-{idx + 1}",
                "quantity": int(row["PCS"]),
                "x": float(row["x"]),
                "y": float(row["y"]),
            }
        )

    return {
        "order_lines": order_lines,
        "constraints": {
            "equipment_mode": mode,
            "ladder_must_stay_in_aisle": False,
            "start_position": {"aisle": "A1", "level": "1", "x": 0.0, "y": 5.5},
        },
        "idempotency_key": "verify-run",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="data/fixtures/mendeley_sample.csv")
    parser.add_argument("--mode", default="walker", choices=["walker", "forklift"])
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

    client = TestClient(app)
    headers = {"X-API-Key": "dev"}

    health = client.get("/v1/health")
    assert health.status_code == 200

    payload = build_request_from_fixture(fixture_path, args.mode)
    optimize = client.post("/v1/waves/optimize", headers=headers, json=payload)
    assert optimize.status_code == 200, optimize.text
    optimize_data = optimize.json()["data"]
    run_id = optimize_data["run_id"]
    assert optimize_data["status"] == "succeeded"

    run = client.get(f"/v1/runs/{run_id}", headers=headers)
    assert run.status_code == 200, run.text
    run_data = run.json()["data"]
    assert run_data["status"] == "succeeded"

    result = run_data["result"]
    assert result["total_distance_m"] > 0
    assert any(seg["segment_type"] == "pick" for seg in result["sequence"])
    assert any(seg["segment_type"] == "ladder_relocate" for seg in result["sequence"])

    print(json.dumps({"status": "ok", "run_id": run_id}, indent=2))


if __name__ == "__main__":
    main()
