#!/usr/bin/env python3
# ruff: noqa: E402
"""
Healthcare MVP Pilot Checks
===========================
End-to-end validation of the healthcare MVP without requiring a browser
or microphone.

This script exercises:
  1. FastAPI health endpoints.
  2. Dashboard patient lookup and follow-up listing.
  3. A simulated phone call using HealthcareReceptionist + tools.
  4. Verification that the follow-up record appears in the dashboard.
  5. WebRTC offer endpoint validation.

Exit code 0 if all checks pass, non-zero otherwise.

Usage:
    python scripts/pilot_healthcare_mvp.py

For a live server test (optional):
    python scripts/pilot_healthcare_mvp.py --live --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on path.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.healthcare_mvp_main import app
from src.domains.healthcare_mvp.domain import HealthcareDomain
from src.domains.healthcare_mvp.seed import (
    clear_follow_up_records,
    get_patient_follow_ups,
)
from src.infrastructure.interfaces import LLMPort


class _PilotLLMClient(LLMPort):
    """Deterministic LLM that drives the healthcare ReAct loop through a call."""

    def __init__(self) -> None:
        self._turn = 0
        self._tool_plan = [
            {
                "tool": "record_symptom",
                "args": {"patient_id": "P-1001", "symptom": "mild headache", "severity": "mild"},
            },
            {
                "tool": "record_medicine_adherence",
                "args": {"patient_id": "P-1001", "taking_medicines": "partially", "missed_reason": "forgot morning dose"},
            },
            {
                "tool": "record_side_effect",
                "args": {"patient_id": "P-1001", "side_effect": "mild nausea", "serious": False},
            },
            {
                "tool": "save_follow_up_summary",
                "args": {
                    "patient_id": "P-1001",
                    "call_id": "PILOT-CALL-001",
                    "well_being_status": "improving",
                    "escalation_needed": False,
                    "callback_requested": False,
                    "notes": "Pilot end-to-end check.",
                },
            },
        ]

    def chat_completion(self, messages, tools=None, temperature=0.7):
        # First phase: return tool call if any planned.
        if self._turn < len(self._tool_plan) * 2:
            step = self._tool_plan[self._turn // 2]
            if self._turn % 2 == 0:
                self._turn += 1
                return {
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_{self._turn}",
                        "function": {"name": step["tool"], "arguments": json.dumps(step["args"])},
                    }],
                }
            # Second phase: natural response after tool result.
            self._turn += 1
            return {"content": "Acknowledged. I noted that for the care team."}
        return {"content": "Thank you. Your follow-up is complete. Take care."}


def _run_dashboard_checks(base_url: str, live: bool) -> None:
    """Check dashboard endpoints via HTTP."""
    if live:
        import requests

        def get(path):
            return requests.get(f"{base_url}{path}")
    else:
        from fastapi.testclient import TestClient

        client = TestClient(app)

        def get(path):
            return client.get(path)

    print("[1/5] Health checks...")
    r = get("/health/live")
    assert r.status_code == 200, f"/health/live failed: {r.status_code}"
    assert r.json()["status"] == "alive"

    r = get("/health/ready")
    assert r.status_code == 200, f"/health/ready failed: {r.status_code}"

    print("[2/5] Dashboard patient endpoints...")
    r = get("/healthcare/dashboard/patients")
    assert r.status_code == 200
    patients = r.json()
    assert patients["total"] >= 3

    r = get("/healthcare/dashboard/patients?q=Ramesh")
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = get("/healthcare/dashboard/patients/P-1001")
    assert r.status_code == 200
    detail = r.json()
    assert detail["patient"]["name"] == "Ramesh Rao"
    assert "follow_ups" in detail

    print("[3/5] WebRTC offer validation...")
    if live:
        r = requests.post("/webrtc/offer?phone=+919876543210", json={"sdp": "", "type": "offer"})
    else:
        with TestClient(app) as client:
            r = client.post("/webrtc/offer?phone=+919876543210", json={"sdp": "", "type": "offer"})
    assert r.status_code == 400
    assert "session_id" in r.text.lower()


async def _run_simulated_call() -> None:
    """Run a scripted conversation and save a follow-up record."""
    print("[4/5] Simulated receptionist call flow...")
    clear_follow_up_records()

    domain = HealthcareDomain()
    receptionist = domain.create_receptionist(llm_client=_PilotLLMClient())

    greeting = await receptionist.handle_call_start(
        session_id="PILOT-CALL-001",
        caller="+919876543210",
        called="healthcare-mvp",
    )
    assert "Ramesh" in greeting

    # Patient mentions symptoms, adherence, side effects, and closes.
    turns = [
        "I have a mild headache.",
        "I forgot my morning dose.",
        "I feel a little nauseous after the medicine.",
        "That is all, thank you.",
    ]
    for turn in turns:
        response = await receptionist.handle_transcript("PILOT-CALL-001", turn)
        assert response and isinstance(response, str)

    # Save summary was the last tool; verify it landed in the store.
    records = get_patient_follow_ups("P-1001")
    assert len(records) == 1, f"Expected 1 follow-up record, got {len(records)}"
    record = records[0]
    assert record.call_id == "PILOT-CALL-001"
    assert record.well_being_status == "improving"
    assert record.taking_medicines == "partially"
    assert any("headache" in s for s in record.symptoms_reported)
    assert any("nausea" in s for s in record.side_effects_reported)
    print(f"      Saved record: {record.call_id} | well-being={record.well_being_status}")


def _run_dashboard_record_verification(base_url: str, live: bool) -> None:
    """Verify the saved record is visible on the dashboard."""
    print("[5/5] Dashboard record verification...")
    if live:
        import requests

        def get(path):
            return requests.get(f"{base_url}{path}")
    else:
        from fastapi.testclient import TestClient

        client = TestClient(app)

        def get(path):
            return client.get(path)

    r = get("/healthcare/dashboard/follow-ups?patient_id=P-1001")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["follow_ups"][0]["call_id"] == "PILOT-CALL-001"

    r = get("/healthcare/dashboard/follow-ups/PILOT-CALL-001")
    assert r.status_code == 200
    assert r.json()["call_id"] == "PILOT-CALL-001"


def main() -> int:
    parser = argparse.ArgumentParser(description="Healthcare MVP pilot checks")
    parser.add_argument("--live", action="store_true", help="Test a running server instead of TestClient")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for live mode")
    args = parser.parse_args()

    try:
        _run_dashboard_checks(args.base_url, args.live)
        asyncio.run(_run_simulated_call())
        _run_dashboard_record_verification(args.base_url, args.live)
    except AssertionError as exc:
        print(f"\n❌ PILOT FAILED: {exc}")
        return 1
    except Exception as exc:
        print(f"\n❌ PILOT ERROR: {exc}")
        import traceback

        traceback.print_exc()
        return 1

    print("\n✅ Healthcare MVP pilot checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
