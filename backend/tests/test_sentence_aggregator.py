"""
Tests for SentenceAggregator
Ref: Pipecat SentenceAggregator pattern; SigArch 2026 streaming TTS.
"""

import pytest
from src.streaming.sentence_aggregator import SentenceAggregator


class TestSentenceAggregator:
    def test_basic_sentence(self):
        agg = SentenceAggregator()
        result = list(agg.ingest("Hello world."))
        assert len(result) == 1
        assert result[0].text == "Hello world."
        assert result[0].is_complete is True

    def test_multiple_sentences_in_one_token(self):
        agg = SentenceAggregator()
        result = list(agg.ingest("First sentence. Second sentence."))
        assert len(result) == 2
        assert result[0].text == "First sentence."
        assert result[1].text == "Second sentence."

    def test_sentence_across_tokens(self):
        agg = SentenceAggregator()
        result1 = list(agg.ingest("Hello wor"))
        assert len(result1) == 0
        result2 = list(agg.ingest("ld. Next sentence."))
        assert len(result2) == 2
        assert result2[0].text == "Hello world."
        assert result2[1].text == "Next sentence."

    def test_abbreviation_dr(self):
        agg = SentenceAggregator()
        result = list(agg.ingest("Meet Dr. Smith today."))
        assert len(result) == 1
        assert "Dr" in result[0].text
        assert "Smith" in result[0].text

    def test_decimal_number(self):
        agg = SentenceAggregator()
        result = list(agg.ingest("The value is 3.14 today."))
        assert len(result) == 1
        assert "3.14" in result[0].text

    def test_flush_remainder(self):
        agg = SentenceAggregator()
        list(agg.ingest("Complete sentence."))
        result = list(agg.ingest("Incomplete"))
        assert len(result) == 0
        rem = agg.flush()
        assert rem is not None
        assert rem.text == "Incomplete"
        assert rem.is_complete is False

    def test_barge_in_reset(self):
        agg = SentenceAggregator()
        list(agg.ingest("Some text"))
        agg.reset()
        rem = agg.flush()
        assert rem is None

    def test_minimum_length(self):
        agg = SentenceAggregator()
        result = list(agg.ingest("Hi."))
        assert len(result) == 0
        rem = agg.flush()
        assert rem.text == "Hi."

    def test_exclamation_and_question(self):
        agg = SentenceAggregator()
        result = list(agg.ingest("Hello! How are you?"))
        assert len(result) == 2
        assert result[0].text == "Hello!"
        assert result[1].text == "How are you?"


# References
# [^3]: Gandhi, S., et al. (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. arXiv:2311.00430.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
