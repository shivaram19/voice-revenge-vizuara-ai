"""
Healthcare Domain Tools
=======================
Tools for patient follow-up calls: lookup, symptom recording, medicine
adherence tracking, follow-up scheduling, and escalation.

Ref: ADR-009; Yao et al. 2023 (ReAct) [^74].
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.domains.healthcare_mvp.seed import (
    FollowUpRecord,
    Patient,
    add_follow_up_record,
)
from src.receptionist.tools.base import Tool, ToolResult


class LookupPatientTool(Tool):
    """Look up a patient by phone number."""

    def __init__(self, patients: dict[str, Patient]) -> None:
        self.patients = patients

    @property
    def name(self) -> str:
        return "lookup_patient"

    @property
    def description(self) -> str:
        return "Find patient details by phone number. Use this at call start."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "phone": {
                    "type": "string",
                    "description": "Patient phone number including country code, e.g. +919876543210",
                },
            },
            "required": ["phone"],
        }

    async def execute(self, phone: str) -> ToolResult:
        patient = self.patients.get(phone)
        if not patient:
            return ToolResult(
                success=False,
                message="I don't see a patient with this number in our records.",
                data={},
            )

        meds = ", ".join(
            f"{m.name} {m.dosage} ({m.frequency})" for m in patient.medications
        )
        return ToolResult(
            success=True,
            message=(
                f"Patient found: {patient.name}, age {patient.age}, "
                f"last visit {patient.last_visit_date}. Medicines: {meds}."
            ),
            data={
                "patient_id": patient.patient_id,
                "name": patient.name,
                "age": patient.age,
                "language_preference": patient.language_preference,
                "diagnosis": patient.diagnosis,
                "medications": [
                    {
                        "name": m.name,
                        "dosage": m.dosage,
                        "frequency": m.frequency,
                        "instructions": m.instructions,
                    }
                    for m in patient.medications
                ],
            },
        )


class RecordSymptomTool(Tool):
    """Record symptoms reported by the patient during the call."""

    def __init__(self) -> None:
        self._buffer: dict[str, list[str]] = {}

    @property
    def name(self) -> str:
        return "record_symptom"

    @property
    def description(self) -> str:
        return (
            "Record a symptom or health update reported by the patient. "
            "Call this whenever the patient mentions a symptom."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "symptom": {"type": "string", "description": "Symptom described by patient"},
                "severity": {
                    "type": "string",
                    "enum": ["mild", "moderate", "severe"],
                    "description": "How bad the symptom seems",
                },
            },
            "required": ["patient_id", "symptom"],
        }

    async def execute(
        self, patient_id: str, symptom: str, severity: str = "mild"
    ) -> ToolResult:
        self._buffer.setdefault(patient_id, []).append(f"{symptom} ({severity})")
        return ToolResult(
            success=True,
            message=f"Noted: {symptom}.",
            data={"patient_id": patient_id, "symptom": symptom, "severity": severity},
        )

    def get_symptoms(self, patient_id: str) -> list[str]:
        return self._buffer.get(patient_id, [])

    def clear(self, patient_id: str) -> None:
        self._buffer.pop(patient_id, None)


class RecordMedicineAdherenceTool(Tool):
    """Record whether the patient is taking prescribed medicines."""

    def __init__(self) -> None:
        self._status: dict[str, dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "record_medicine_adherence"

    @property
    def description(self) -> str:
        return (
            "Record the patient's medicine adherence. Use after asking "
            "'Are you taking your medicines as prescribed?'"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "taking_medicines": {
                    "type": "string",
                    "enum": ["yes", "no", "partially", "unsure"],
                },
                "missed_reason": {
                    "type": "string",
                    "description": "Why the patient missed doses, if applicable",
                },
            },
            "required": ["patient_id", "taking_medicines"],
        }

    async def execute(
        self,
        patient_id: str,
        taking_medicines: str,
        missed_reason: str = "",
    ) -> ToolResult:
        self._status[patient_id] = {
            "taking_medicines": taking_medicines,
            "missed_reason": missed_reason,
        }
        if taking_medicines == "yes":
            msg = "Great, thank you for continuing your medicines."
        elif taking_medicines == "partially":
            msg = "Thank you for being honest. Let's make sure we note that."
        elif taking_medicines == "no":
            msg = "I understand. I will note this for the doctor's team."
        else:
            msg = "That's okay, I will make a note of it."
        return ToolResult(
            success=True,
            message=msg,
            data=self._status[patient_id],
        )

    def get_status(self, patient_id: str) -> dict[str, Any]:
        return self._status.get(patient_id, {})


class RecordSideEffectTool(Tool):
    """Record any medicine side effects reported by the patient."""

    def __init__(self) -> None:
        self._buffer: dict[str, list[str]] = {}

    @property
    def name(self) -> str:
        return "record_side_effect"

    @property
    def description(self) -> str:
        return (
            "Record a side effect the patient reports from their medicine. "
            "Escalate if the side effect is serious."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "side_effect": {"type": "string"},
                "serious": {
                    "type": "boolean",
                    "description": "True if serious or concerning",
                },
            },
            "required": ["patient_id", "side_effect"],
        }

    async def execute(
        self, patient_id: str, side_effect: str, serious: bool = False
    ) -> ToolResult:
        self._buffer.setdefault(patient_id, []).append(side_effect)
        if serious:
            msg = (
                "I have noted this side effect. Please contact your doctor "
                "or visit the hospital immediately."
            )
        else:
            msg = "I have noted this. Please mention it to your doctor on the next visit."
        return ToolResult(
            success=True,
            message=msg,
            data={"side_effect": side_effect, "serious": serious},
        )

    def get_side_effects(self, patient_id: str) -> list[str]:
        return self._buffer.get(patient_id, [])


class ScheduleFollowupTool(Tool):
    """Schedule a follow-up call or appointment reminder."""

    def __init__(self) -> None:
        self._scheduled: dict[str, list[str]] = {}

    @property
    def name(self) -> str:
        return "schedule_followup"

    @property
    def description(self) -> str:
        return (
            "Schedule a follow-up action for the patient, such as a callback "
            "or appointment reminder. Use if the patient asks for a callback "
            "or if escalation is needed."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "followup_type": {
                    "type": "string",
                    "enum": ["doctor_callback", "nurse_callback", "appointment_reminder"],
                },
                "reason": {"type": "string"},
                "preferred_time": {"type": "string"},
            },
            "required": ["patient_id", "followup_type", "reason"],
        }

    async def execute(
        self,
        patient_id: str,
        followup_type: str,
        reason: str,
        preferred_time: str = "",
    ) -> ToolResult:
        self._scheduled.setdefault(patient_id, []).append(
            {"type": followup_type, "reason": reason, "preferred_time": preferred_time}
        )
        return ToolResult(
            success=True,
            message="I have scheduled a follow-up for you. Someone from the hospital will reach out.",
            data={
                "patient_id": patient_id,
                "followup_type": followup_type,
                "reason": reason,
                "preferred_time": preferred_time,
            },
        )


class EscalationTool(Tool):
    """Flag a call for immediate doctor or nurse attention."""

    @property
    def name(self) -> str:
        return "escalate_to_care_team"

    @property
    def description(self) -> str:
        return (
            "Use when the patient reports serious symptoms, severe side effects, "
            "or any condition requiring urgent medical attention. Tell the patient "
            "to seek immediate care."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["patient_id", "reason"],
        }

    async def execute(self, patient_id: str, reason: str) -> ToolResult:
        return ToolResult(
            success=True,
            message=(
                "I am flagging this for the care team right away. Please call "
                "the hospital emergency number or visit the nearest emergency department."
            ),
            data={"patient_id": patient_id, "reason": reason, "escalated": True},
        )


class SaveFollowUpSummaryTool(Tool):
    """Persist the follow-up call summary for hospital dashboard review."""

    def __init__(
        self,
        symptom_tool: RecordSymptomTool,
        adherence_tool: RecordMedicineAdherenceTool,
        side_effect_tool: RecordSideEffectTool,
        schedule_tool: ScheduleFollowupTool,
    ) -> None:
        self.symptom_tool = symptom_tool
        self.adherence_tool = adherence_tool
        self.side_effect_tool = side_effect_tool
        self.schedule_tool = schedule_tool

    @property
    def name(self) -> str:
        return "save_follow_up_summary"

    @property
    def description(self) -> str:
        return (
            "Call this at the end of the follow-up call to save the summary "
            "for the hospital care team. Only call once, before hanging up."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "call_id": {"type": "string"},
                "well_being_status": {
                    "type": "string",
                    "enum": ["improving", "same", "worse", "concerning"],
                },
                "escalation_needed": {"type": "boolean"},
                "escalation_reason": {"type": "string"},
                "callback_requested": {"type": "boolean"},
                "notes": {"type": "string"},
            },
            "required": ["patient_id", "call_id", "well_being_status"],
        }

    async def execute(
        self,
        patient_id: str,
        call_id: str,
        well_being_status: str,
        escalation_needed: bool = False,
        escalation_reason: str = "",
        callback_requested: bool = False,
        notes: str = "",
    ) -> ToolResult:
        adherence = self.adherence_tool.get_status(patient_id)
        record = FollowUpRecord(
            call_id=call_id,
            patient_id=patient_id,
            timestamp=datetime.utcnow(),
            call_connected=True,
            spoke_to_patient=True,
            well_being_status=well_being_status,
            symptoms_reported=self.symptom_tool.get_symptoms(patient_id),
            taking_medicines=adherence.get("taking_medicines", ""),
            missed_medicine_reason=adherence.get("missed_reason", ""),
            side_effects_reported=self.side_effect_tool.get_side_effects(patient_id),
            escalation_needed=escalation_needed,
            escalation_reason=escalation_reason,
            callback_requested=callback_requested,
            notes=notes,
        )
        add_follow_up_record(record)

        # Clean up per-call buffers.
        self.symptom_tool.clear(patient_id)

        return ToolResult(
            success=True,
            message="Thank you. Your follow-up has been recorded.",
            data={"record_id": call_id},
        )


# References
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
