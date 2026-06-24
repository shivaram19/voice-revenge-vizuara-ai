"""
Healthcare Dashboard API
========================
Read-only endpoints for hospital staff to review follow-up call outcomes.

Ref: ADR-009
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.domains.healthcare_mvp.dashboard import (
    get_all_follow_up_summaries,
    get_patient_progress,
)
from src.domains.healthcare_mvp.seed import (
    PatientNotFoundError,
    get_patient,
    search_patients,
)

router = APIRouter(prefix="/healthcare/dashboard", tags=["healthcare-dashboard"])


@router.get("/patients")
async def list_patients(
    q: str | None = Query(None, description="Search by name or phone"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List patients with optional name/phone search."""
    patients = search_patients(q, limit=limit, offset=offset)
    return {
        "total": len(patients),
        "patients": [
            {
                "id": p.patient_id,
                "name": p.name,
                "phone": p.phone,
                "language_preference": p.language_preference,
                "diagnosis": p.diagnosis,
            }
            for p in patients
        ],
    }


@router.get("/patients/{patient_id}")
async def get_patient_detail(patient_id: str):
    """Return patient profile plus all follow-up history."""
    try:
        patient = get_patient(patient_id)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    progress = get_patient_progress(patient_id)
    return {
        "patient": {
            "id": patient.patient_id,
            "name": patient.name,
            "phone": patient.phone,
            "age": patient.age,
            "language_preference": patient.language_preference,
            "diagnosis": patient.diagnosis,
            "last_visit_date": patient.last_visit_date.isoformat(),
            "medications": [
                {
                    "name": med.name,
                    "dosage": med.dosage,
                    "frequency": med.frequency,
                    "prescribed_date": med.prescribed_date.isoformat(),
                    "duration_days": med.duration_days,
                    "instructions": med.instructions,
                }
                for med in patient.medications
            ],
            "appointments": [
                {
                    "department": appt.department,
                    "doctor_name": appt.doctor_name,
                    "scheduled_at": appt.appointment_date.isoformat() if appt.appointment_date else None,
                    "notes": appt.notes,
                }
                for appt in patient.appointments
            ],
        },
        **progress,
    }


@router.get("/follow-ups")
async def list_follow_ups(
    patient_id: str | None = Query(None),
    escalation_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
):
    """List follow-up records, optionally filtered by patient or escalations."""
    records = get_all_follow_up_summaries()
    if patient_id:
        records = [r for r in records if r["patient_id"] == patient_id]
    if escalation_only:
        records = [r for r in records if r["escalation_needed"]]
    records = records[:limit]
    return {"total": len(records), "follow_ups": records}


@router.get("/follow-ups/{call_id}")
async def get_follow_up(call_id: str):
    """Return a single follow-up record by call_id."""
    for record in get_all_follow_up_summaries():
        if record["call_id"] == call_id:
            return record
    raise HTTPException(status_code=404, detail=f"Follow-up call {call_id} not found")
