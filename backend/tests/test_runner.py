"""
Standalone test runner — zero dependencies.
Clarity-driven: tests either pass or fail. No skipping. No maybes.
"""

import sys
import traceback
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.streaming.sentence_aggregator import SentenceAggregator


class TestFailure(Exception):
    pass


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise TestFailure(f"{msg} Expected {expected!r}, got {actual!r}")


def assert_true(value, msg=""):
    if not value:
        raise TestFailure(f"{msg} Expected True, got {value!r}")


def assert_is_not_none(value, msg=""):
    if value is None:
        raise TestFailure(f"{msg} Expected not None")


def assert_is_none(value, msg=""):
    if value is not None:
        raise TestFailure(f"{msg} Expected None, got {value!r}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_basic_sentence():
    agg = SentenceAggregator()
    result = list(agg.ingest("Hello world."))
    assert_eq(len(result), 1, "count")
    assert_eq(result[0].text, "Hello world.", "text")
    assert_true(result[0].is_complete, "complete")


def test_multiple_sentences_in_one_token():
    agg = SentenceAggregator()
    result = list(agg.ingest("First sentence. Second sentence."))
    assert_eq(len(result), 2, "count")
    assert_eq(result[0].text, "First sentence.", "first")
    assert_eq(result[1].text, "Second sentence.", "second")


def test_sentence_across_tokens():
    agg = SentenceAggregator()
    result1 = list(agg.ingest("Hello wor"))
    assert_eq(len(result1), 0, "first chunk")
    result2 = list(agg.ingest("ld. Next sentence."))
    assert_eq(len(result2), 2, "second chunk count")
    assert_eq(result2[0].text, "Hello world.", "first sentence")
    assert_eq(result2[1].text, "Next sentence.", "second sentence")


def test_abbreviation_dr():
    agg = SentenceAggregator()
    result = list(agg.ingest("Meet Dr. Smith today."))
    assert_eq(len(result), 1, "count")
    assert_true("Dr" in result[0].text, "Dr preserved")
    assert_true("Smith" in result[0].text, "Smith preserved")


def test_decimal_number():
    agg = SentenceAggregator()
    result = list(agg.ingest("The value is 3.14 today."))
    assert_eq(len(result), 1, "count")
    assert_true("3.14" in result[0].text, "decimal preserved")


def test_flush_remainder():
    agg = SentenceAggregator()
    list(agg.ingest("Complete sentence."))
    result = list(agg.ingest("Incomplete"))
    assert_eq(len(result), 0, "no sentence yet")
    rem = agg.flush()
    assert_is_not_none(rem, "remainder exists")
    assert_eq(rem.text, "Incomplete", "remainder text")
    assert_true(not rem.is_complete, "remainder incomplete")


def test_barge_in_reset():
    agg = SentenceAggregator()
    list(agg.ingest("Some text"))
    agg.reset()
    rem = agg.flush()
    assert_is_none(rem, "reset clears buffer")


def test_minimum_length():
    agg = SentenceAggregator()
    result = list(agg.ingest("Hi."))
    assert_eq(len(result), 0, "too short")
    rem = agg.flush()
    assert_eq(rem.text, "Hi.", "flushed short text")


def test_exclamation_and_question():
    agg = SentenceAggregator()
    result = list(agg.ingest("Hello! How are you?"))
    assert_eq(len(result), 2, "count")
    assert_eq(result[0].text, "Hello!", "exclamation")
    assert_eq(result[1].text, "How are you?", "question")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    test_basic_sentence,
    test_multiple_sentences_in_one_token,
    test_sentence_across_tokens,
    test_abbreviation_dr,
    test_decimal_number,
    test_flush_remainder,
    test_barge_in_reset,
    test_minimum_length,
    test_exclamation_and_question,
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    for test in TESTS:
        name = test.__name__
        try:
            test()
            print(f"PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {name}")
            traceback.print_exc()
            failed += 1

    print()
    print(f"RESULT: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


# References
# [^3]: Gandhi, S., et al. (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. arXiv:2311.00430.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
