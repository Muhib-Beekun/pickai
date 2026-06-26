from fastapi.testclient import TestClient

from pickai.api.main import app


client = TestClient(app)
HEADERS = {"X-API-Key": "dev"}


def test_facility_profile_roundtrip():
    get_resp = client.get("/v1/facility/profile", headers=HEADERS)
    assert get_resp.status_code == 200
    profile = get_resp.json()["data"]
    assert profile["tenant_id"] == "default"
    assert profile["facility_id"] == "main"
    assert len(profile["locations"]) > 0

    profile["resources"]["pickers"] = 2
    put_resp = client.put("/v1/facility/profile", json=profile, headers=HEADERS)
    assert put_resp.status_code == 200
    assert put_resp.json()["data"]["resources"]["pickers"] == 2


def test_facility_export_geojson():
    resp = client.get("/v1/facility/profile/export?format=geojson", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["data"]["type"] == "FeatureCollection"
    assert resp.json()["meta"]["facility_profile_version"] >= 1


def test_tasks_optimize_endpoint():
    profile = client.get("/v1/facility/profile", headers=HEADERS).json()["data"]
    loc = profile["locations"][0]
    payload = {
        "tasks": [
            {
                "task_type": "pick",
                "order_id": "o1",
                "line_id": "l1",
                "sku": "sku-1",
                "location_id": loc["location_id"],
                "quantity": 1,
                "x": loc["x"],
                "y": loc["y"],
            },
            {
                "task_type": "pick",
                "order_id": "o1",
                "line_id": "l2",
                "sku": "sku-2",
                "location_id": profile["locations"][1]["location_id"],
                "quantity": 1,
                "x": profile["locations"][1]["x"],
                "y": profile["locations"][1]["y"],
            },
        ],
        "constraints": {"equipment_mode": "walker", "ladder_must_stay_in_aisle": False},
        "facility_profile_version": profile["version"],
        "idempotency_key": "tasks-api-test",
    }
    resp = client.post("/v1/tasks/optimize", json=payload, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["run_id"] == "tasks-api-test"
    assert len(data["assignments"]) >= 1
    assert data["processing_time_ms"] >= 0
