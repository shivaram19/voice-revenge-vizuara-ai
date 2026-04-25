"""
Tests for Receptionist Tool Suite
Zero dependencies. Clarity-driven: pass or fail.

Ref: Test methodology follows sigarch zero-dep approach.
All assertions use assert_eq / assert_true for deterministic output.
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime, timedelta

# Fix module path for src/ imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.receptionist.tools.contact_lookup import ContactDirectory, Contact
from src.receptionist.tools.calendar import Calendar
from src.receptionist.tools.faq import FAQKnowledgeBase, FAQChunk
from src.receptionist.tools.messages import MessageLog


class TestFailure(Exception):
    pass


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise TestFailure(f"{msg} Expected {expected!r}, got {actual!r}")


def assert_true(value, msg=""):
    if not value:
        raise TestFailure(f"{msg} Expected True, got {value!r}")


# ---------------------------------------------------------------------------
# Contact Lookup Tests
# ---------------------------------------------------------------------------

def test_contact_lookup_by_name():
    dir = ContactDirectory()
    dir.add(Contact("Alice Smith", "Engineer", "Engineering", "101", "alice@example.com"))
    results = dir.lookup("Alice")
    assert_eq(len(results), 1, "count")
    assert_eq(results[0].name, "Alice Smith", "name")


def test_contact_lookup_by_department():
    dir = ContactDirectory()
    dir.add(Contact("Bob Jones", "Manager", "Sales", "202", "bob@example.com"))
    results = dir.lookup("Sales")
    assert_eq(len(results), 1, "count")
    assert_eq(results[0].department, "Sales", "dept")


def test_contact_voice_formatting():
    dir = ContactDirectory()
    dir.add(Contact("Carol White", "CEO", "Executive", "001", "carol@example.com"))
    text = dir.format_for_voice(dir.lookup("Carol"))
    assert_true("Carol White" in text, "name in voice")


# ---------------------------------------------------------------------------
# Calendar Tests
# ---------------------------------------------------------------------------

def test_calendar_availability():
    cal = Calendar()
    cal.add_service("Consultation")
    date = datetime(2026, 4, 28, 0, 0)
    slots = cal.check_availability("Consultation", date)
    assert_true(len(slots) > 0, "has slots")


def test_calendar_booking():
    cal = Calendar()
    cal.add_service("Consultation")
    start = datetime(2026, 4, 28, 10, 0)
    result = cal.book("Consultation", start, 30, "Patient A")
    assert_true(result.success, "booking success")
    assert_true("10:00 AM" in result.message, "time in message")


def test_calendar_double_booking():
    cal = Calendar()
    cal.add_service("Consultation")
    start = datetime(2026, 4, 28, 10, 0)
    cal.book("Consultation", start, 30, "Patient A")
    result = cal.book("Consultation", start, 30, "Patient B")
    assert_true(not result.success, "double booking rejected")


# ---------------------------------------------------------------------------
# FAQ Tests
# ---------------------------------------------------------------------------

def test_faq_search():
    kb = FAQKnowledgeBase()
    kb.add(FAQChunk("Hours are 9 to 5.", "handbook", "hours"))
    kb.add(FAQChunk("We are at 123 Main St.", "handbook", "location"))
    results = kb.search("hours")
    assert_true(len(results) > 0, "found result")
    assert_true("9 to 5" in results[0].text, "correct chunk")


def test_faq_voice_formatting():
    kb = FAQKnowledgeBase()
    kb.add(FAQChunk("Hours are 9 to 5. Closed weekends. More text here.", "handbook", "hours"))
    text = kb.format_for_voice(kb.search("hours"))
    assert_true("9 to 5" in text, "content preserved")
    assert_true(text.endswith("."), "ends with period")


# ---------------------------------------------------------------------------
# Message Tests
# ---------------------------------------------------------------------------

def test_message_recording():
    log = MessageLog()
    msg = log.record("John", "+1555", "Dr. Smith", "Call me back", urgent=True)
    assert_eq(msg.recipient, "Dr. Smith", "recipient")
    assert_true(msg.urgent, "urgent flag")


def test_message_formatting():
    log = MessageLog()
    msg = log.record("John", "+1555", "Dr. Smith", "Call me back")
    text = log.format_confirmation_for_voice(msg)
    assert_true("Dr. Smith" in text, "recipient in voice")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    test_contact_lookup_by_name,
    test_contact_lookup_by_department,
    test_contact_voice_formatting,
    test_calendar_availability,
    test_calendar_booking,
    test_calendar_double_booking,
    test_faq_search,
    test_faq_voice_formatting,
    test_message_recording,
    test_message_formatting,
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


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^14]: Qiu, J., et al. (2026). VoiceAgentRAG. arXiv:2603.02206.
# [^28]: Newman, S. (2015). Building Microservices. O'Reilly.
