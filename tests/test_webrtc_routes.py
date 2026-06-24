"""
Tests for WebRTC routes.
"""
import os
from pathlib import Path

# record_ui.py creates its recordings directory at import time. Point it at a
# writable location inside the repo so tests can import the FastAPI app.
os.environ.setdefault(
    "RECORDINGS_DIR",
    str(Path(__file__).parent.parent / "recordings"),
)

# The project's .env may contain placeholder Azure credentials; disable
# telemetry so importing the app does not fail during test collection.
os.environ.setdefault("APPLICATIONINSIGHTS_CONNECTION_STRING", "")

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_webrtc_offer_requires_session_id(client):
    response = client.post("/webrtc/offer", json={"sdp": "v=0\n", "type": "offer"})
    assert response.status_code == 400
    assert "session_id" in response.json()["detail"].lower()


def test_webrtc_offer_returns_503_when_engine_disabled(client):
    response = client.post(
        "/webrtc/offer?session_id=abc", json={"sdp": "v=0\n", "type": "offer"}
    )
    assert response.status_code == 503


def test_webrtc_ice_servers_returns_default_stun(client):
    response = client.get("/webrtc/ice-servers")
    assert response.status_code == 200
    data = response.json()
    assert "iceServers" in data
    assert any("stun:" in s["urls"] for s in data["iceServers"])
