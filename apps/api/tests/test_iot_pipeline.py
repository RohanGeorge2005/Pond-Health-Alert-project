import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_ingest_iot_reading_unauthorized():
    payload = {
        "pond_id": "pond-demo-1",
        "device_id": "ESP32-POND-01",
        "temperature": 27.5,
        "ph": 7.4,
        "dissolved_oxygen": 6.2,
    }
    # No token header -> 401
    resp = client.post("/api/iot/readings", json=payload)
    assert resp.status_code == 401


def test_ingest_iot_reading_authorized_normal():
    payload = {
        "pond_id": "pond-demo-1",
        "device_id": "ESP32-POND-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 27.5,
        "ph": 7.4,
        "dissolved_oxygen": 6.2,
        "ammonia": 0.015,
        "battery_pct": 95.0,
        "signal_rssi": -65,
        "is_simulated": False,
    }
    headers = {"X-Device-Token": "esp32_secret_key_pond01"}
    resp = client.post("/api/iot/readings", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["assessment_status"] in ["green", "amber"]
    assert data["device_online"] is True


def test_ingest_iot_reading_triggers_hypoxia_alert():
    # Dissolved oxygen crash below 3.0 mg/L -> Must trigger RED
    payload = {
        "pond_id": "pond-demo-1",
        "device_id": "ESP32-POND-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 27.5,
        "ph": 7.4,
        "dissolved_oxygen": 2.1,
        "ammonia": 0.015,
        "is_simulated": True,
    }
    headers = {"X-Device-Token": "esp32_secret_key_pond01"}
    resp = client.post("/api/iot/readings", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment_status"] == "red"
    assert "CRITICAL_LOW_DO" in data["reason_codes"]


def test_device_health_endpoint():
    resp = client.get("/api/iot/devices/ESP32-POND-01/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == "ESP32-POND-01"
    assert "battery_level_pct" in data
    assert "signal_rssi" in data
    assert data["is_online"] is True


def test_device_health_unknown_device_404():
    resp = client.get("/api/iot/devices/UNKNOWN-DEV-99/health")
    assert resp.status_code == 404


def test_batch_ingest_iot_readings():
    payload = {
        "device_id": "ESP32-POND-01",
        "readings": [
            {
                "reading_id": "batch-r1",
                "pond_id": "pond-demo-1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "temperature": 27.2,
                "ph": 7.3,
                "dissolved_oxygen": 5.8,
            },
            {
                "reading_id": "batch-r2",
                "pond_id": "pond-demo-1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "temperature": 27.3,
                "ph": 7.35,
                "dissolved_oxygen": 5.9,
            },
        ],
    }
    headers = {"X-Device-Token": "esp32_secret_key_pond01"}
    resp = client.post("/api/iot/readings/batch", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["ingested_count"] >= 1

