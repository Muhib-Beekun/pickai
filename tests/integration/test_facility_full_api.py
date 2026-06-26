from fastapi.testclient import TestClient

from pickai.api.main import app

client = TestClient(app)
HEADERS = {"X-API-Key": "dev"}


def test_slotting_suggestions_endpoint():
    resp = client.get("/v1/facility/slotting/suggestions", headers=HEADERS)
    assert resp.status_code == 200
    assert "data" in resp.json()


def test_patch_aisle_status():
    resp = client.patch("/v1/facility/aisles/A1?status=blocked", headers=HEADERS)
    assert resp.status_code == 200
    client.patch("/v1/facility/aisles/A1?status=open", headers=HEADERS)


def test_simulate_endpoint():
    profile = client.get("/v1/facility/profile", headers=HEADERS).json()["data"]
    draft = profile.copy()
    draft["resources"]["pickers"] = 2
    resp = client.post("/v1/facility/simulate?sample_size=20", json=draft, headers=HEADERS)
    assert resp.status_code == 200
    assert "roi_pct" in resp.json()["data"]
