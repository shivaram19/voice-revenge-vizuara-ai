"""
Tests for HealthcareReceptionist call flow.

Uses a mock LLM client to verify:
  - Patient lookup by phone at call start.
  - Greeting is personalized and language-aware.
  - Transcripts are forwarded through the ReAct loop.
  - Tool calls are executed and the final response is returned.
"""

from __future__ import annotations

import pytest

from src.domains.healthcare_mvp.domain import HealthcareDomain
from src.domains.healthcare_mvp.seed import get_patient_follow_ups


@pytest.fixture
def domain_receptionist(mock_llm):
    domain = HealthcareDomain()
    return domain.create_receptionist(llm_client=mock_llm)


@pytest.mark.asyncio
async def test_call_start_greeting_english_patient(domain_receptionist):
    greeting = await domain_receptionist.handle_call_start(
        session_id="S-001", caller="+919876543212", called="healthcare-mvp"
    )
    assert "Kiran" in greeting
    assert "Arogya Hospital" in greeting
    assert domain_receptionist.patient is not None
    assert domain_receptionist.patient.patient_id == "P-1003"


@pytest.mark.asyncio
async def test_call_start_greeting_telugu_patient(domain_receptionist):
    greeting = await domain_receptionist.handle_call_start(
        session_id="S-002", caller="+919876543211", called="healthcare-mvp"
    )
    assert "Lakshmi" in greeting or "Namaste" in greeting
    assert domain_receptionist.patient.language_preference == "te"


@pytest.mark.asyncio
async def test_call_start_unknown_patient(domain_receptionist):
    greeting = await domain_receptionist.handle_call_start(
        session_id="S-003", caller="+910000000000", called="healthcare-mvp"
    )
    assert domain_receptionist.patient is None
    assert "namaste" in greeting.lower()


@pytest.mark.asyncio
async def test_transcript_direct_response(domain_receptionist, mock_llm):
    await domain_receptionist.handle_call_start(
        session_id="S-004", caller="+919876543210", called="healthcare-mvp"
    )
    mock_llm.responses = [{"content": "I am glad to hear that."}]
    response = await domain_receptionist.handle_transcript("S-004", "I am feeling fine.")
    assert response == "I am glad to hear that."


@pytest.mark.asyncio
async def test_transcript_tool_call_record_symptom(domain_receptionist, mock_llm):
    await domain_receptionist.handle_call_start(
        session_id="S-005", caller="+919876543210", called="healthcare-mvp"
    )
    mock_llm.add_tool_call(
        "record_symptom",
        {"patient_id": "P-1001", "symptom": "headache", "severity": "mild"},
    )
    # Phase 2 response after tool execution.
    mock_llm.responses.append({"content": "I have noted the headache."})

    response = await domain_receptionist.handle_transcript("S-005", "I have a mild headache.")
    assert "headache" in response.lower()
    records = get_patient_follow_ups("P-1001")
    assert len(records) == 0  # not saved yet


@pytest.mark.asyncio
async def test_save_summary_tool(domain_receptionist, mock_llm):
    await domain_receptionist.handle_call_start(
        session_id="S-006", caller="+919876543210", called="healthcare-mvp"
    )
    # Simulate adherence recording and summary save in one turn.
    mock_llm.add_tool_call(
        "record_medicine_adherence",
        {"patient_id": "P-1001", "taking_medicines": "yes"},
    )
    mock_llm.responses.append({"content": "Great, keep it up."})
    await domain_receptionist.handle_transcript("S-006", "Yes I am taking medicines.")

    mock_llm.add_tool_call(
        "save_follow_up_summary",
        {
            "patient_id": "P-1001",
            "call_id": "S-006",
            "well_being_status": "improving",
        },
    )
    mock_llm.responses.append({"content": "Thank you. Have a good day."})
    response = await domain_receptionist.handle_transcript("S-006", "That is all, thank you.")

    assert "thank you" in response.lower()
    records = get_patient_follow_ups("P-1001")
    assert len(records) == 1
    assert records[0].taking_medicines == "yes"
