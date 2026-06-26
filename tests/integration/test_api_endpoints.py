from fastapi.testclient import TestClient

from pickai.api.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_optimize_and_poll_flow():
    payload = {
        "order_lines": [
            {
                "order_id": "o1",
                "line_id": "l1",
                "sku": "sku-1",
                "location_id": "loc-1",
                "quantity": 1,
                "x": 1,
                "y": 9,
            },
            {
                "order_id": "o1",
                "line_id": "l2",
                "sku": "sku-2",
                "location_id": "loc-2",
                "quantity": 1,
                "x": 2,
                "y": 11,
            },
        ],
        "constraints": {"equipment_mode": "walker", "ladder_must_stay_in_aisle": False},
        "idempotency_key": "api-test-run",
    }
    headers = {"X-API-Key": "dev"}

    optimize = client.post("/v1/waves/optimize", json=payload, headers=headers)
    assert optimize.status_code == 200
    run_id = optimize.json()["data"]["run_id"]

    run = client.get(f"/v1/runs/{run_id}", headers=headers)
    assert run.status_code == 200
    assert run.json()["data"]["status"] == "succeeded"
