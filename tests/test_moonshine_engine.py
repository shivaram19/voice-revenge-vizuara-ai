"""
Tests for Moonshine v2 streaming ASR engine.
"""
import asyncio

import numpy as np
import pytest

from src.asr.moonshine_engine import (
    MoonshineTranscriptEvent,
    _StreamingEventListener,
    _to_list_float,
)


class FakeTranscriptLine:
    def __init__(
        self,
        text: str,
        line_id: int,
        is_complete: bool = False,
        has_text_changed: bool = True,
        start_time: float = 0.0,
        duration: float = 0.0,
        latency_ms: float = 100.0,
    ):
        self.text = text
        self.line_id = line_id
        self.is_complete = is_complete
        self.has_text_changed = has_text_changed
        self.start_time = start_time
        self.duration = duration
        self.last_transcription_latency_ms = latency_ms


class FakeTranscriptEvent:
    def __init__(self, line):
        self.line = line


def test_to_list_float_mono_unchanged():
    arr = np.array([0.1, -0.2, 0.3], dtype=np.float32)
    result = _to_list_float(arr)
    assert result == pytest.approx([0.1, -0.2, 0.3])


def test_to_list_float_stereo_to_mono():
    arr = np.array([[0.2, 0.4], [0.4, 0.8]], dtype=np.float32)
    result = _to_list_float(arr)
    assert result == pytest.approx([0.3, 0.6])


@pytest.mark.asyncio
async def test_listener_emits_partial_and_final():
    queue = asyncio.Queue()
    listener = _StreamingEventListener(queue)

    listener(FakeTranscriptEvent(FakeTranscriptLine("hello", 1, is_complete=False)))
    listener(FakeTranscriptEvent(FakeTranscriptLine("hello world", 1, is_complete=False)))
    listener(FakeTranscriptEvent(FakeTranscriptLine("hello world!", 1, is_complete=True)))
    # Duplicate final should be ignored.
    listener(FakeTranscriptEvent(FakeTranscriptLine("hello world!", 1, is_complete=True)))

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    assert len(events) == 3
    assert events[0].text == "hello"
    assert events[0].is_partial is True
    assert events[0].is_final is False
    assert events[2].text == "hello world!"
    assert events[2].is_partial is False
    assert events[2].is_final is True


@pytest.mark.asyncio
async def test_listener_deduplicates_partial_text():
    queue = asyncio.Queue()
    listener = _StreamingEventListener(queue)

    listener(FakeTranscriptEvent(FakeTranscriptLine("same", 1, is_complete=False)))
    listener(FakeTranscriptEvent(FakeTranscriptLine("same", 1, is_complete=False)))
    listener(FakeTranscriptEvent(FakeTranscriptLine("changed", 1, is_complete=False)))

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    texts = [e.text for e in events]
    assert texts == ["same", "changed"]


@pytest.mark.asyncio
async def test_listener_ignores_non_text_changes():
    queue = asyncio.Queue()
    listener = _StreamingEventListener(queue)

    listener(
        FakeTranscriptEvent(
            FakeTranscriptLine("hello", 1, is_complete=False, has_text_changed=False)
        )
    )
    assert queue.empty()
