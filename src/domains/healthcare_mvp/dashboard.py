"""
Healthcare MVP Dashboard Helpers
=================================
Read-only helpers for exposing follow-up records to hospital staff.

Ref: ADR-009; human-centered design for care-team visibility.
"""

from __future__ import annotations

from src.domains.healthcare_mvp.seed import (
    FollowUpRecord,
    get_all_follow_ups,
    get_patient_follow_ups,
)


def follow_up_to_dict(record: FollowUpRecord) -> dict:
    """Serialize a FollowUpRecord for API responses."""
    return {
        "call_id": record.call_id,
        "patient_id": record.patient_id,
        "timestamp": record.timestamp.isoformat(),
        "call_connected": record.call_connected,
        "spoke_to_patient": record.spoke_to_patient,
        "well_being_status": record.well_being_status,
        "symptoms_reported": record.symptoms_reported,
        "taking_medicines": record.taking_medicines,
        "missed_medicine_reason": record.missed_medicine_reason,
        "side_effects_reported": record.side_effects_reported,
        "escalation_needed": record.escalation_needed,
        "escalation_reason": record.escalation_reason,
        "callback_requested": record.callback_requested,
        "notes": record.notes,
    }


def get_patient_progress(patient_id: str) -> dict:
    """Return all follow-up records for a patient."""
    records = get_patient_follow_ups(patient_id)
    return {
        "patient_id": patient_id,
        "follow_ups": [follow_up_to_dict(r) for r in records],
    }


def get_all_follow_up_summaries() -> list[dict]:
    """Return all follow-up records across patients, newest first."""
    return [follow_up_to_dict(r) for r in get_all_follow_ups()]
