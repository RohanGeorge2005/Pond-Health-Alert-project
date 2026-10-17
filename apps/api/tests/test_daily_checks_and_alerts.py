import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from apps.api.main import app, alerts_db

client = TestClient(app)

def test_daily_check_submission_and_persistence():
    payload = {
        "check_id": "chk-test-01",
        "pond_id": "pond-demo-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "feeding": "normal",
        "behavior": "normal",
        "dead_fish_count": 0,
        "notes": "Morning routine inspection - fish swimming vigorously",
    }
    resp = client.post("/daily-checks", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["check_id"] == "chk-test-01"


def test_daily_check_invalid_pond_returns_404():
    payload = {
        "check_id": "chk-test-02",
        "pond_id": "non-existent-pond-999",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "feeding": "normal",
        "behavior": "normal",
        "dead_fish_count": 0,
    }
    resp = client.post("/daily-checks", json=payload)
    assert resp.status_code == 404


def test_high_mortality_escalates_to_red():
    # Dead fish count > 5 must trigger RED with HIGH_FISH_MORTALITY
    payload = {
        "check_id": "chk-test-mortality",
        "pond_id": "pond-demo-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "feeding": "none",
        "behavior": "slow",
        "dead_fish_count": 8,
    }
    resp = client.post("/daily-checks", json=payload)
    assert resp.status_code == 200

    # Verify pond status reflects red
    status_resp = client.get("/ponds/pond-demo-1/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "red"
    assert "HIGH_FISH_MORTALITY" in status_data["reason_codes"]


def test_alerts_endpoint_and_acknowledgment():
    # Ingest a critical low DO reading to guarantee an active alert
    payload = {
        "pond_id": "pond-demo-1",
        "device_id": "ESP32-POND-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 27.5,
        "ph": 7.4,
        "dissolved_oxygen": 1.9,
    }
    client.post("/api/iot/readings", json=payload, headers={"X-Device-Token": "esp32_secret_key_pond01"})

    resp = client.get("/ponds/pond-demo-1/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) > 0

    alert_id = alerts[0]["alert_id"]
    ack_resp = client.post(f"/alerts/{alert_id}/ack")
    assert ack_resp.status_code == 200
    assert ack_resp.json()["acknowledged"] is True
