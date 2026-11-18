"""Pruebas de integración para los endpoints REST del motor de entrenamiento."""
import pytest
from starlette.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_training_defaults(client):
    res = client.get("/api/v1/training/config/defaults")
    assert res.status_code == 200
    data = res.json()
    assert "m1_random_forest" in data
    assert "m2_xgboost" in data
    assert "m3_isolation_forest" in data


def test_api_training_eda(client):
    res = client.get("/api/v1/training/eda?use_demo=true")
    assert res.status_code == 200
    data = res.json()
    assert data["total_records"] > 0
    assert "active_directory_telemetry" in data


def test_api_training_start_and_jobs(client):
    payload = {
        "run_m1": True,
        "run_m2": False,
        "run_m3": False,
        "use_optuna": False,
        "use_demo_dataset": True,
        "actor": "test_auditor@demo.local",
    }
    start_res = client.post("/api/v1/training/start", json=payload)
    assert start_res.status_code == 200
    body = start_res.json()
    assert body["status"] == "started"
    job_id = body["job_id"]

    jobs_res = client.get("/api/v1/training/jobs")
    assert jobs_res.status_code == 200
    jobs_list = jobs_res.json()["jobs"]
    assert any(j["job_id"] == job_id for j in jobs_list)
