"""
Tests for Healthcare MVP dashboard helpers.
"""

from datetime import datetime

import pytest

from src.domains.healthcare_mvp.dashboard import (
    follow_up_to_dict,
    get_all_follow_up_summaries,
    get_patient_progress,
)
from src.domains.healthcare_mvp.seed import (
    FollowUpRecord,
    add_follow_up_record,
    clear_follow_up_records,
)


@pytest.fixture(autouse=True)
def reset_records():
    clear_follow_up_records()
    yield
    clear_follow_up_records()


def test_follow_up_to_dict_shape():
    record = FollowUpRecord(
        call_id="CALL-001",
        patient_id="P-1001",
        timestamp=datetime(2026, 6, 23, 10, 0, 0),
        call_connected=True,
        spoke_to_patient=True,
        well_being_status="improving",
        symptoms_reported=["headache (mild)"],
        taking_medicines="yes",
        side_effects_reported=[],
        escalation_needed=False,
        callback_requested=False,
        notes="All good.",
    )
    d = follow_up_to_dict(record)
    assert d["call_id"] == "CALL-001"
    assert d["patient_id"] == "P-1001"
    assert d["timestamp"] == "2026-06-23T10:00:00"
    assert d["well_being_status"] == "improving"


def test_patient_progress_and_summaries():
    add_follow_up_record(
        FollowUpRecord(
            call_id="CALL-001",
            patient_id="P-1001",
            timestamp=datetime(2026, 6, 23, 10, 0, 0),
            call_connected=True,
            spoke_to_patient=True,
            well_being_status="improving",
        )
    )
    add_follow_up_record(
        FollowUpRecord(
            call_id="CALL-002",
            patient_id="P-1002",
            timestamp=datetime(2026, 6, 24, 10, 0, 0),
            call_connected=True,
            spoke_to_patient=True,
            well_being_status="concerning",
            escalation_needed=True,
        )
    )

    progress = get_patient_progress("P-1001")
    assert progress["patient_id"] == "P-1001"
    assert len(progress["follow_ups"]) == 1

    all_summaries = get_all_follow_up_summaries()
    assert len(all_summaries) == 2
    assert all_summaries[0]["call_id"] == "CALL-002"  # newest first
