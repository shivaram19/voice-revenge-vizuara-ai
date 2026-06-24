"""
Healthcare Domain Seed Data
===========================
In-memory patient registry, medication records, and follow-up history for
dev/test. In production this should be backed by a real EHR or patient CRM.

Ref: ADR-009 (Domain Modularity)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass
class Medication:
    name: str
    dosage: str
    frequency: str  # e.g., "twice daily after food"
    prescribed_date: date
    duration_days: int
    instructions: str = ""


@dataclass
class Appointment:
    appointment_date: datetime
    department: str
    doctor_name: str
    notes: str = ""


@dataclass
class Patient:
    patient_id: str
    name: str
    phone: str
    age: int
    gender: str
    language_preference: str  # "en", "te", or "te-en"
    last_visit_date: date
    diagnosis: str
    medications: list[Medication] = field(default_factory=list)
    appointments: list[Appointment] = field(default_factory=list)


@dataclass
class FollowUpRecord:
    call_id: str
    patient_id: str
    timestamp: datetime
    call_connected: bool
    spoke_to_patient: bool
    well_being_status: str = ""  # improving / same / worse / concerning
    symptoms_reported: list[str] = field(default_factory=list)
    taking_medicines: str = ""  # yes / no / partially / unsure
    missed_medicine_reason: str = ""
    side_effects_reported: list[str] = field(default_factory=list)
    escalation_needed: bool = False
    escalation_reason: str = ""
    callback_requested: bool = False
    notes: str = ""


class PatientNotFoundError(Exception):
    """Raised when a patient lookup fails."""


# In-memory stores. Production should use a database.
_follow_up_records: list[FollowUpRecord] = []
_FOLLOW_UP_LOG_PATH: Path | None = None


def set_follow_up_log_path(path: str | None) -> None:
    """Set the JSONL file path for persisting follow-up records."""
    global _FOLLOW_UP_LOG_PATH
    _FOLLOW_UP_LOG_PATH = Path(path) if path else None


def _record_to_dict(record: FollowUpRecord) -> dict:
    """Serialize a FollowUpRecord to a JSON-friendly dict."""
    d = asdict(record)
    # Convert datetime/date objects to ISO strings.
    d["timestamp"] = record.timestamp.isoformat()
    return d


# Lazy patient registry so seed data is created on first access.
_patients_db: dict[str, Patient] | None = None


def _patients() -> dict[str, Patient]:
    """Return the in-memory patient registry keyed by phone number."""
    global _patients_db
    if _patients_db is None:
        _patients_db = seed_healthcare_db()["patients"]
    return _patients_db


def get_patient_by_phone(phone: str) -> Patient | None:
    """Look up a patient by phone number."""
    return _patients().get(phone)


def get_patient(patient_id: str) -> Patient:
    """Look up a patient by patient_id. Raises PatientNotFoundError if missing."""
    for patient in _patients().values():
        if patient.patient_id == patient_id:
            return patient
    raise PatientNotFoundError(f"Patient {patient_id} not found")


def get_patient_id_by_phone(phone: str) -> str | None:
    """Return the patient_id for a phone number, if known."""
    patient = _patients().get(phone)
    return patient.patient_id if patient else None


def search_patients(query: str | None = None, limit: int = 100, offset: int = 0) -> list[Patient]:
    """Search patients by name or phone. Returns all patients if query is empty."""
    patients = list(_patients().values())
    if query:
        q = query.strip().lower()
        patients = [
            p for p in patients
            if q in p.name.lower() or q in p.phone or q in p.patient_id.lower()
        ]
    return patients[offset:offset + limit]


def add_follow_up_record(record: FollowUpRecord) -> None:
    """Append a follow-up record to the in-memory store and JSONL log."""
    _follow_up_records.append(record)
    if _FOLLOW_UP_LOG_PATH is not None:
        try:
            _FOLLOW_UP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _FOLLOW_UP_LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(_record_to_dict(record), ensure_ascii=False) + "\n")
        except Exception:
            # MVP: silently ignore persistence failures; production should alert.
            pass


def get_patient_follow_ups(patient_id: str) -> list[FollowUpRecord]:
    """Return all follow-up records for a patient, newest first."""
    return sorted(
        [r for r in _follow_up_records if r.patient_id == patient_id],
        key=lambda r: r.timestamp,
        reverse=True,
    )


def get_all_follow_ups() -> list[FollowUpRecord]:
    """Return all follow-up records, newest first."""
    return sorted(_follow_up_records, key=lambda r: r.timestamp, reverse=True)


def clear_follow_up_records() -> None:
    """Clear all in-memory follow-up records. Useful for tests."""
    _follow_up_records.clear()


def seed_healthcare_db() -> dict[str, dict[str, Patient]]:
    """Create mock patient registry keyed by phone number."""
    patients: dict[str, Patient] = {
        "+919876543210": Patient(
            patient_id="P-1001",
            name="Ramesh Rao",
            phone="+919876543210",
            age=58,
            gender="male",
            language_preference="te-en",
            last_visit_date=date(2026, 6, 20),
            diagnosis="Hypertension and Type 2 Diabetes",
            medications=[
                Medication(
                    name="Telma H",
                    dosage="40 mg",
                    frequency="once daily in the morning",
                    prescribed_date=date(2026, 6, 20),
                    duration_days=30,
                    instructions="Take after breakfast",
                ),
                Medication(
                    name="Metformin",
                    dosage="500 mg",
                    frequency="twice daily after food",
                    prescribed_date=date(2026, 6, 20),
                    duration_days=30,
                    instructions="Take after lunch and dinner",
                ),
            ],
            appointments=[
                Appointment(
                    appointment_date=datetime(2026, 7, 20, 10, 0),
                    department="General Medicine",
                    doctor_name="Dr. Priya Sharma",
                    notes="Routine BP and sugar check",
                ),
            ],
        ),
        "+919876543211": Patient(
            patient_id="P-1002",
            name="Lakshmi Devi",
            phone="+919876543211",
            age=42,
            gender="female",
            language_preference="te",
            last_visit_date=date(2026, 6, 22),
            diagnosis="Post-operative follow-up after gallbladder surgery",
            medications=[
                Medication(
                    name="Combiflam",
                    dosage="1 tablet",
                    frequency="twice daily after food",
                    prescribed_date=date(2026, 6, 22),
                    duration_days=7,
                    instructions="Take only if pain is present",
                ),
            ],
            appointments=[
                Appointment(
                    appointment_date=datetime(2026, 6, 29, 11, 0),
                    department="Surgery",
                    doctor_name="Dr. Anand Reddy",
                    notes="Stitch removal and wound check",
                ),
            ],
        ),
        "+919876543212": Patient(
            patient_id="P-1003",
            name="Kiran Kumar",
            phone="+919876543212",
            age=35,
            gender="male",
            language_preference="en",
            last_visit_date=date(2026, 6, 23),
            diagnosis="Upper respiratory infection",
            medications=[
                Medication(
                    name="Azithromycin",
                    dosage="500 mg",
                    frequency="once daily",
                    prescribed_date=date(2026, 6, 23),
                    duration_days=5,
                    instructions="Take before food",
                ),
            ],
            appointments=[
                Appointment(
                    appointment_date=datetime(2026, 6, 30, 9, 30),
                    department="General Medicine",
                    doctor_name="Dr. Priya Sharma",
                    notes="Review if cough persists",
                ),
            ],
        ),
    }

    return {"patients": patients}
