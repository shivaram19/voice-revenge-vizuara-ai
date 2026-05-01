"""
Tests for Scheduling Engine & Contractor Tools
Zero dependencies. Clarity-driven.
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime, date, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.receptionist.models import Database, Contractor, Appointment, AppointmentStatus, AppointmentType, CallTask, CallTaskStatus
from src.receptionist.scheduler import SchedulingEngine
from src.receptionist.tools.contractor_tools import ContractorDirectory, OutboundCallManager


class TestFailure(Exception):
    pass


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise TestFailure(f"{msg} Expected {expected!r}, got {actual!r}")


def assert_true(value, msg=""):
    if not value:
        raise TestFailure(f"{msg} Expected True, got {value!r}")


# ---------------------------------------------------------------------------
# Setup helper
# ---------------------------------------------------------------------------

def fresh_db():
    """Return a fresh in-memory database."""
    return Database(":memory:")


# ---------------------------------------------------------------------------
# Contractor Tests
# ---------------------------------------------------------------------------

def test_add_and_get_contractor():
    db = fresh_db()
    cid = db.add_contractor(Contractor(
        id=None, name="John Smith", phone="5550101", email="john@example.com",
        specialty="Plumbing", daily_limit=5,
    ))
    c = db.get_contractor(cid)
    assert_eq(c.name, "John Smith", "name")
    assert_eq(c.specialty, "Plumbing", "specialty")
    assert_eq(c.daily_limit, 5, "daily_limit")


def test_find_contractors_by_specialty():
    db = fresh_db()
    tools = ContractorDirectory(db)
    db.add_contractor(Contractor(id=None, name="Plumber Joe", phone="5550101", email="joe@example.com", specialty="Plumbing"))
    db.add_contractor(Contractor(id=None, name="Electrician Amy", phone="5550102", email="amy@example.com", specialty="Electrical"))
    results = tools.find_contractors("plumb")
    assert_eq(len(results), 1, "count")
    assert_eq(results[0].name, "Plumber Joe", "name")


# ---------------------------------------------------------------------------
# Availability Tests
# ---------------------------------------------------------------------------

def test_available_slots_basic():
    db = fresh_db()
    scheduler = SchedulingEngine(db)
    cid = db.add_contractor(Contractor(id=None, name="Test", phone="5550000", email="t@example.com", specialty="General"))

    target = date(2026, 5, 15)
    slots = scheduler.get_available_slots(cid, target)
    assert_true(len(slots) > 0, "has slots")
    assert_eq(slots[0].start_time.hour, 8, "first slot at 8am")


def test_available_slots_respects_existing_appointment():
    db = fresh_db()
    scheduler = SchedulingEngine(db)
    cid = db.add_contractor(Contractor(id=None, name="Test", phone="5550000", email="t@example.com", specialty="General"))

    target = date(2026, 5, 15)
    # Book 10:00 AM
    ten_am = datetime(2026, 5, 15, 10, 0)
    scheduler.book_appointment(cid, "Alice", "5551111", ten_am, 30)

    slots = scheduler.get_available_slots(cid, target)
    start_times = [s.start_time for s in slots]

    # 10:00 AM should NOT be available (30 min appt + 15 min buffer = blocked until 10:45)
    assert_true(ten_am not in start_times, "10am blocked")
    # 10:30 AM should NOT be available (within buffer)
    ten_thirty = datetime(2026, 5, 15, 10, 30)
    assert_true(ten_thirty not in start_times, "10:30am blocked by buffer")
    # 11:00 AM should be available
    eleven = datetime(2026, 5, 15, 11, 0)
    assert_true(eleven in start_times, "11am available")


# ---------------------------------------------------------------------------
# Booking Tests
# ---------------------------------------------------------------------------

def test_book_appointment_success():
    db = fresh_db()
    scheduler = SchedulingEngine(db)
    cid = db.add_contractor(Contractor(id=None, name="Test", phone="5550000", email="t@example.com", specialty="General"))

    start = datetime(2026, 5, 15, 14, 0)
    success, message, appt_id = scheduler.book_appointment(cid, "Bob", "5552222", start, 30)
    assert_true(success, "booking success")
    assert_true(appt_id is not None, "appointment id returned")
    assert_true("Booked" in message, "confirmation message")


def test_book_appointment_conflict():
    db = fresh_db()
    scheduler = SchedulingEngine(db)
    cid = db.add_contractor(Contractor(id=None, name="Test", phone="5550000", email="t@example.com", specialty="General"))

    start = datetime(2026, 5, 15, 14, 0)
    scheduler.book_appointment(cid, "Bob", "5552222", start, 30)

    # Try to book same slot
    success, message, appt_id = scheduler.book_appointment(cid, "Charlie", "5553333", start, 30)
    assert_true(not success, "double booking rejected")
    assert_true("no longer available" in message.lower(), "correct error message")


def test_book_appointment_outside_hours():
    db = fresh_db()
    scheduler = SchedulingEngine(db)
    cid = db.add_contractor(Contractor(id=None, name="Test", phone="5550000", email="t@example.com", specialty="General"))

    start = datetime(2026, 5, 15, 6, 0)  # 6 AM — before business hours
    success, message, appt_id = scheduler.book_appointment(cid, "Bob", "5552222", start, 30)
    assert_true(not success, "outside hours rejected")


def test_book_appointment_daily_limit():
    db = fresh_db()
    scheduler = SchedulingEngine(db)
    cid = db.add_contractor(Contractor(id=None, name="Test", phone="5550000", email="t@example.com", specialty="General", daily_limit=2))

    # Book 2 appointments (the limit)
    scheduler.book_appointment(cid, "A", "5550001", datetime(2026, 5, 15, 9, 0), 30)
    scheduler.book_appointment(cid, "B", "5550002", datetime(2026, 5, 15, 10, 0), 30)

    # Third should fail
    success, message, appt_id = scheduler.book_appointment(cid, "C", "5550003", datetime(2026, 5, 15, 11, 0), 30)
    assert_true(not success, "daily limit enforced")
    assert_true("limit" in message.lower(), "mentions limit")


# ---------------------------------------------------------------------------
# Cancellation & Reschedule Tests
# ---------------------------------------------------------------------------

def test_cancel_appointment():
    db = fresh_db()
    scheduler = SchedulingEngine(db)
    cid = db.add_contractor(Contractor(id=None, name="Test", phone="5550000", email="t@example.com", specialty="General"))

    start = datetime(2026, 5, 15, 14, 0)
    _, _, appt_id = scheduler.book_appointment(cid, "Bob", "5552222", start, 30)

    success, message = scheduler.cancel_appointment(appt_id)
    assert_true(success, "cancel success")

    # Slot should now be available
    slots = scheduler.get_available_slots(cid, date(2026, 5, 15))
    start_times = [s.start_time for s in slots]
    assert_true(start in start_times, "slot freed after cancel")


def test_reschedule_appointment():
    db = fresh_db()
    scheduler = SchedulingEngine(db)
    cid = db.add_contractor(Contractor(id=None, name="Test", phone="5550000", email="t@example.com", specialty="General"))

    old_start = datetime(2026, 5, 15, 14, 0)
    _, _, appt_id = scheduler.book_appointment(cid, "Bob", "5552222", old_start, 30)

    new_start = datetime(2026, 5, 15, 16, 0)
    success, message, new_id = scheduler.reschedule_appointment(appt_id, new_start)
    assert_true(success, "reschedule success")
    assert_true(new_id is not None, "new appointment id")

    # Old slot free, new slot taken
    slots = scheduler.get_available_slots(cid, date(2026, 5, 15))
    start_times = [s.start_time for s in slots]
    assert_true(old_start in start_times, "old slot freed")
    assert_true(new_start not in start_times, "new slot taken")


# ---------------------------------------------------------------------------
# Outbound Call Tests
# ---------------------------------------------------------------------------

def test_create_call_task():
    db = fresh_db()
    manager = OutboundCallManager(db)
    cid = db.add_contractor(Contractor(id=None, name="Plumber Joe", phone="5550101", email="joe@example.com", specialty="Plumbing"))

    success, message, task_id = manager.schedule_call_to_contractor(cid, "Emergency leak repair")
    assert_true(success, "task created")
    assert_true(task_id > 0, "task id returned")
    assert_true("Plumber Joe" in message, "contractor name in message")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    test_add_and_get_contractor,
    test_find_contractors_by_specialty,
    test_available_slots_basic,
    test_available_slots_respects_existing_appointment,
    test_book_appointment_success,
    test_book_appointment_conflict,
    test_book_appointment_outside_hours,
    test_book_appointment_daily_limit,
    test_cancel_appointment,
    test_reschedule_appointment,
    test_create_call_task,
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    for test in TESTS:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}")
            traceback.print_exc()
            failed += 1

    print()
    print(f"RESULT: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
