import io
import pytest
import numpy as np
import cv2
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def create_synthetic_image(is_blurry: bool = False, is_dark: bool = False) -> bytes:
    """Generates a synthetic image in JPEG format for testing."""
    if is_dark:
        # Solid dark image -> fails exposure gate
        img = np.zeros((300, 300, 3), dtype=np.uint8)
    elif is_blurry:
        # Uniform color -> Laplacian variance = 0 -> fails blur gate
        img = np.full((300, 300, 3), 128, dtype=np.uint8)
    else:
        # Rich texture with sharp edges and moderate brightness -> passes gate
        img = np.zeros((300, 300, 3), dtype=np.uint8)
        # Add varied noise and shapes
        for i in range(0, 300, 20):
            cv2.line(img, (i, 0), (300 - i, 300), (200, 150, 100), 2)
            cv2.circle(img, (i, i), 15, (50, 220, 120), -1)
        # Normal lighting
        img = np.clip(img + 80, 0, 255).astype(np.uint8)

    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()


def test_photo_analyze_non_image_rejected():
    files = {"file": ("test.txt", b"plain text content", "text/plain")}
    resp = client.post("/api/fish/analyze", data={"pond_id": "pond-demo-1"}, files=files)
    assert resp.status_code == 400
    assert "Invalid file format" in resp.json()["detail"]


def test_photo_analyze_empty_file_rejected():
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    resp = client.post("/api/fish/analyze", data={"pond_id": "pond-demo-1"}, files=files)
    assert resp.status_code == 400
    assert "Empty image file" in resp.json()["detail"]


def test_photo_analyze_fails_quality_gate_returns_retake_tips():
    blurry_bytes = create_synthetic_image(is_blurry=True)
    files = {"file": ("blurry.jpg", blurry_bytes, "image/jpeg")}
    resp = client.post("/api/fish/analyze", data={"pond_id": "pond-demo-1"}, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed_gate"] is False
    assert len(data["gate_failure_reasons"]) > 0
    assert len(data["tips_en"]) > 0
    assert len(data["tips_kn"]) > 0
    assert data["gradcam_data_url"] is None


def test_photo_analyze_passes_quality_gate_returns_predictions_and_gradcam():
    good_bytes = create_synthetic_image(is_blurry=False)
    files = {"file": ("fish.jpg", good_bytes, "image/jpeg")}
    resp = client.post("/api/fish/analyze", data={"pond_id": "pond-demo-1"}, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed_gate"] is True
    assert data["predicted_class"] is not None
    assert "confidence" in data
    assert "confidence_pct" in data
    assert data["confidence_pct"] >= 0
    assert data["label_en"] is not None
    assert data["label_kn"] is not None
    assert len(data["next_steps_en"]) > 0
    assert len(data["next_steps_kn"]) > 0
    assert "disclaimer_en" in data
    # Check Grad-CAM Base64 Data URL format
    if data["gradcam_data_url"]:
        assert data["gradcam_data_url"].startswith("data:image/jpeg;base64,")
