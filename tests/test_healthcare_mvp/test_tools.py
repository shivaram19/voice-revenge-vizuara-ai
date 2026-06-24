"""
Tests for Healthcare MVP tools.

Verifies that each tool in the Goal-Engineering toolset
(lookup, symptom, adherence, side-effect, schedule, escalate, save)
returns the expected shape and populates shared buffers correctly.
"""

from __future__ import annotations

import pytest

from src.domains.healthcare_mvp.seed import (
    get_patient_follow_ups,
    seed_healthcare_db,
)
from src.domains.healthcare_mvp.tools import (
    EscalationTool,
    LookupPatientTool,
    RecordMedicineAdherenceTool,
    RecordSideEffectTool,
    RecordSymptomTool,
    SaveFollowUpSummaryTool,
    ScheduleFollowupTool,
)


@pytest.fixture
def patients():
    return seed_healthcare_db()["patients"]


@pytest.mark.asyncio
async def test_lookup_patient_found(patients):
    tool = LookupPatientTool(patients)
    result = await tool.execute(phone="+919876543210")
    assert result.success is True
    assert "Ramesh Rao" in result.message
    assert result.data["patient_id"] == "P-1001"


@pytest.mark.asyncio
async def test_lookup_patient_not_found(patients):
    tool = LookupPatientTool(patients)
    result = await tool.execute(phone="+910000000000")
    assert result.success is False
    assert "don't see" in result.message


@pytest.mark.asyncio
async def test_record_symptom():
    tool = RecordSymptomTool()
    result = await tool.execute(patient_id="P-1001", symptom="headache", severity="mild")
    assert result.success is True
    assert tool.get_symptoms("P-1001") == ["headache (mild)"]


@pytest.mark.asyncio
async def test_record_medicine_adherence():
    tool = RecordMedicineAdherenceTool()
    result = await tool.execute(
        patient_id="P-1001", taking_medicines="partially", missed_reason="forgot morning dose"
    )
    assert result.success is True
    status = tool.get_status("P-1001")
    assert status["taking_medicines"] == "partially"
    assert status["missed_reason"] == "forgot morning dose"


@pytest.mark.asyncio
async def test_record_side_effect():
    tool = RecordSideEffectTool()
    result = await tool.execute(patient_id="P-1001", side_effect="mild rash", serious=False)
    assert result.success is True
    assert tool.get_side_effects("P-1001") == ["mild rash"]


@pytest.mark.asyncio
async def test_schedule_followup():
    tool = ScheduleFollowupTool()
    result = await tool.execute(
        patient_id="P-1001",
        followup_type="doctor_callback",
        reason="patient reported chest discomfort",
        preferred_time="tomorrow 10 AM",
    )
    assert result.success is True
    assert "scheduled" in result.message.lower()


@pytest.mark.asyncio
async def test_escalation():
    tool = EscalationTool()
    result = await tool.execute(
        patient_id="P-1001", reason="severe chest pain and difficulty breathing"
    )
    assert result.success is True
    assert result.data["escalated"] is True
    assert "emergency" in result.message.lower()


@pytest.mark.asyncio
async def test_save_follow_up_summary():
    symptom_tool = RecordSymptomTool()
    adherence_tool = RecordMedicineAdherenceTool()
    side_effect_tool = RecordSideEffectTool()
    schedule_tool = ScheduleFollowupTool()

    await symptom_tool.execute(patient_id="P-1001", symptom="headache", severity="mild")
    await adherence_tool.execute(patient_id="P-1001", taking_medicines="yes")
    await side_effect_tool.execute(patient_id="P-1001", side_effect="nausea", serious=False)

    save_tool = SaveFollowUpSummaryTool(
        symptom_tool=symptom_tool,
        adherence_tool=adherence_tool,
        side_effect_tool=side_effect_tool,
        schedule_tool=schedule_tool,
    )
    result = await save_tool.execute(
        patient_id="P-1001",
        call_id="CALL-001",
        well_being_status="improving",
        escalation_needed=False,
        callback_requested=False,
        notes="Patient sounded positive.",
    )

    assert result.success is True
    records = get_patient_follow_ups("P-1001")
    assert len(records) == 1
    record = records[0]
    assert record.call_id == "CALL-001"
    assert record.well_being_status == "improving"
    assert record.taking_medicines == "yes"
    assert "headache (mild)" in record.symptoms_reported
    assert "nausea" in record.side_effects_reported
