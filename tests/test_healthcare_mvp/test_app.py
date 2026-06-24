"""
Integration tests for the standalone Healthcare MVP FastAPI app.

These tests exercise the public HTTP surface (health + dashboard) without
requiring a live Moonshine ASR engine or LLM credentials.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.api.healthcare_mvp_main import app
from src.domains.healthcare_mvp.seed import (
    FollowUpRecord,
    add_follow_up_record,
    clear_follow_up_records,
)


@pytest.fixture
def client():
    clear_follow_up_records()
    with TestClient(app) as c:
        # Ensure moonshine engine is marked absent so we don't accidentally
        # hit ASR code paths in dashboard tests.
        c.app.state.moonshine_engine = None
        yield c
    clear_follow_up_records()


def test_health_live(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_health_ready(client):
    response = client.get("/health/ready")
    assert response.status_code == 200


def test_list_patients(client):
    response = client.get("/healthcare/dashboard/patients")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3


def test_list_patients_search(client):
    response = client.get("/healthcare/dashboard/patients?q=Ramesh")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["patients"][0]["name"] == "Ramesh Rao"


def test_get_patient_detail(client):
    response = client.get("/healthcare/dashboard/patients/P-1001")
    assert response.status_code == 200
    data = response.json()
    assert data["patient"]["name"] == "Ramesh Rao"
    assert "follow_ups" in data


def test_get_patient_detail_not_found(client):
    response = client.get("/healthcare/dashboard/patients/P-9999")
    assert response.status_code == 404


def test_list_follow_ups(client):
    add_follow_up_record(
        FollowUpRecord(
            call_id="CALL-APP-001",
            patient_id="P-1001",
            timestamp=datetime.utcnow(),
            call_connected=True,
            spoke_to_patient=True,
            well_being_status="improving",
        )
    )
    response = client.get("/healthcare/dashboard/follow-ups")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(r["call_id"] == "CALL-APP-001" for r in data["follow_ups"])


def test_list_follow_ups_escalation_filter(client):
    clear_follow_up_records()
    add_follow_up_record(
        FollowUpRecord(
            call_id="CALL-ESC-001",
            patient_id="P-1002",
            timestamp=datetime.utcnow(),
            call_connected=True,
            spoke_to_patient=True,
            well_being_status="concerning",
            escalation_needed=True,
            escalation_reason="severe pain",
        )
    )
    add_follow_up_record(
        FollowUpRecord(
            call_id="CALL-NO-001",
            patient_id="P-1001",
            timestamp=datetime.utcnow(),
            call_connected=True,
            spoke_to_patient=True,
            well_being_status="improving",
            escalation_needed=False,
        )
    )
    response = client.get("/healthcare/dashboard/follow-ups?escalation_only=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["follow_ups"][0]["call_id"] == "CALL-ESC-001"


def test_get_follow_up_by_call_id(client):
    clear_follow_up_records()
    add_follow_up_record(
        FollowUpRecord(
            call_id="CALL-ID-001",
            patient_id="P-1001",
            timestamp=datetime.utcnow(),
            call_connected=True,
            spoke_to_patient=True,
            well_being_status="same",
        )
    )
    response = client.get("/healthcare/dashboard/follow-ups/CALL-ID-001")
    assert response.status_code == 200
    assert response.json()["call_id"] == "CALL-ID-001"


def test_get_follow_up_not_found(client):
    response = client.get("/healthcare/dashboard/follow-ups/NONEXISTENT")
    assert response.status_code == 404


def test_static_demo_served(client):
    response = client.get("/static/healthcare-demo.html")
    assert response.status_code == 200
    assert "Healthcare Patient Follow-Up MVP" in response.text


def test_webrtc_offer_requires_session_id(client):
    response = client.post("/webrtc/offer?phone=+919876543210", json={"sdp": "", "type": "offer"})
    assert response.status_code == 400
    assert "session_id" in response.text.lower()


def test_webrtc_offer_requires_phone(client):
    response = client.post(
        "/webrtc/offer?session_id=S-TEST", json={"sdp": "", "type": "offer"}
    )
    assert response.status_code == 400
    assert "phone" in response.text.lower()


def test_webrtc_offer_returns_503_without_engine(client):
    response = client.post(
        "/webrtc/offer?session_id=S-TEST&phone=+919876543210",
        json={"sdp": "", "type": "offer"},
    )
    assert response.status_code == 503
    assert "moonshine" in response.text.lower()
