"""
Healthcare domain plugin for hospital patient follow-up voice calls.
"""

from src.domains.healthcare_mvp.dashboard import (
    follow_up_to_dict,
    get_all_follow_up_summaries,
    get_patient_progress,
)
from src.domains.healthcare_mvp.domain import HealthcareDomain
from src.domains.healthcare_mvp.prompts import (
    HEALTHCARE_SYSTEM_PROMPT,
    build_healthcare_instructions,
    build_healthcare_prompt,  # noqa: F401
)
from src.domains.healthcare_mvp.receptionist import HealthcareReceptionist
from src.domains.healthcare_mvp.seed import (
    Appointment,
    FollowUpRecord,
    Medication,
    Patient,
    PatientNotFoundError,
    add_follow_up_record,
    get_all_follow_ups,
    get_patient,
    get_patient_by_phone,
    get_patient_follow_ups,
    get_patient_id_by_phone,
    search_patients,
    seed_healthcare_db,
    set_follow_up_log_path,
)

__all__ = [
    "HealthcareDomain",
    "HealthcareReceptionist",
    "HEALTHCARE_SYSTEM_PROMPT",
    "build_healthcare_prompt",
    "build_healthcare_instructions",
    "Patient",
    "Medication",
    "Appointment",
    "FollowUpRecord",
    "PatientNotFoundError",
    "seed_healthcare_db",
    "get_patient_by_phone",
    "get_patient_id_by_phone",
    "get_patient",
    "search_patients",
    "add_follow_up_record",
    "get_patient_follow_ups",
    "get_all_follow_ups",
    "follow_up_to_dict",
    "get_patient_progress",
    "get_all_follow_up_summaries",
    "set_follow_up_log_path",
]
