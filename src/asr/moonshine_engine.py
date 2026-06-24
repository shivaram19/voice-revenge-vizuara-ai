"""
Moonshine v2 Streaming ASR Engine
=================================
Self-hosted English speech-to-text using the Moonshine Voice library.
Wraps the native Transcriber/Stream API in an async, event-driven interface
suitable for real-time WebRTC ingestion.

Research Provenance:
    - Moonshine v2: Ergodic Streaming Encoder ASR for Latency-Critical
      Speech Applications [^King2026]
    - Moonshine Medium Streaming: 245M params, 6.65% WER, 269ms Linux [^Moonshine2026]
    - Streaming models do incremental encoding with KV-cache reuse,
      avoiding Whisper's fixed 30-second window overhead [^Moonshine2026]

Ref: ADR-023 (Self-Hosted WebRTC ASR)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from src.infrastructure.logging_config import get_logger

logger = get_logger("asr.moonshine")


@dataclass
class MoonshineTranscriptEvent:
    """Normalized transcript event from Moonshine streaming."""

    text: str
    is_partial: bool = False
    is_final: bool = False
    line_id: int = 0
    start_time_sec: float = 0.0
    duration_sec: float = 0.0
    latency_ms: float = 0.0


# Moonshine Voice imports are deferred until first use so that importing this
# module does not require a GPU or download models during unit-test collection.
_moonshine_voice: Optional[Any] = None


def _get_moonshine_voice() -> Any:
    global _moonshine_voice
    if _moonshine_voice is None:
        import moonshine_voice as mv

        _moonshine_voice = mv
    return _moonshine_voice


def _to_list_float(audio: np.ndarray) -> List[float]:
    """Moonshine's Stream.add_audio expects a plain Python list of floats."""
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype(np.float32, copy=False).tolist()


class _StreamingEventListener:
    """Bridge between Moonshine's callback API and our async event queue.

    Moonshine fires the listener for every incremental change (new line,
    text changed, line completed). We normalize those into deduplicated
    partial/final events so downstream consumers do not emit duplicate
    WebSocket messages.
    """

    def __init__(self, queue: asyncio.Queue[MoonshineTranscriptEvent]) -> None:
        self._queue = queue
        self._last_text: Dict[int, str] = {}
        self._completed: set = set()

    def __call__(self, event: Any) -> None:
        line = event.line
        line_id = int(line.line_id)
        text = line.text or ""

        if line.is_complete:
            if line_id in self._completed:
                return
            self._completed.add(line_id)
            self._last_text[line_id] = text
            self._queue.put_nowait(
                MoonshineTranscriptEvent(
                    text=text,
                    is_partial=False,
                    is_final=True,
                    line_id=line_id,
                    start_time_sec=float(line.start_time),
                    duration_sec=float(line.duration),
                    latency_ms=float(line.last_transcription_latency_ms),
                )
            )
            return

        if not line.has_text_changed:
            return
        if self._last_text.get(line_id) == text:
            return
        self._last_text[line_id] = text
        self._queue.put_nowait(
            MoonshineTranscriptEvent(
                text=text,
                is_partial=True,
                is_final=False,
                line_id=line_id,
                start_time_sec=float(line.start_time),
                duration_sec=float(line.duration),
                latency_ms=float(line.last_transcription_latency_ms),
            )
        )


class MoonshineStreamingEngine:
    """
    Async wrapper around Moonshine Voice for server-side streaming ASR.

    Usage:
        engine = await MoonshineStreamingEngine.create(language="en")
        stream = await engine.create_stream(session_id="abc")
        async for event in stream.events():
            print(event.text, event.is_final)
        await stream.add_audio(pcm_16k_float32)
        await stream.close()
    """

    def __init__(
        self,
        model_path: str,
        model_arch: Any,
        language: str = "en",
        update_interval_ms: int = 500,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.model_path = model_path
        self.model_arch = model_arch
        self.language = language
        self.update_interval_ms = update_interval_ms
        self.options = options or {}
        self._mv = _get_moonshine_voice()
        self._transcriber = self._mv.Transcriber(
            model_path=Path(model_path),
            model_arch=model_arch,
            update_interval=update_interval_ms / 1000.0,
            options=self.options,
        )
        self._streams: Dict[str, "MoonshineStream"] = {}
        logger.info(
            "moonshine_engine_loaded",
            language=language,
            model_path=model_path,
            model_arch=str(model_arch),
            update_interval_ms=update_interval_ms,
        )

    @classmethod
    async def create(
        cls,
        language: str = "en",
        model_arch: Optional[str] = None,
        update_interval_ms: int = 500,
        options: Optional[Dict[str, Any]] = None,
    ) -> "MoonshineStreamingEngine":
        """Factory: download model if needed and load the transcriber."""
        mv = _get_moonshine_voice()
        if model_arch is not None:
            arch_enum = getattr(mv.ModelArch, model_arch.upper(), None)
            if arch_enum is None:
                raise ValueError(f"Unknown Moonshine model arch: {model_arch}")
            model_path, resolved_arch = mv.get_model_path(arch_enum, language)
        else:
            model_path, resolved_arch = mv.get_model_for_language(language)

        logger.info(
            "moonshine_model_resolved",
            language=language,
            model_path=model_path,
            model_arch=str(resolved_arch),
        )
        # Model loading is synchronous and can take ~1s; run in thread to avoid
        # blocking the event loop during application startup.
        return await asyncio.to_thread(
            cls,
            model_path=model_path,
            model_arch=resolved_arch,
            language=language,
            update_interval_ms=update_interval_ms,
            options=options,
        )

    async def create_stream(self, session_id: str) -> "MoonshineStream":
        """Create a new streaming session."""
        if session_id in self._streams:
            await self._streams[session_id].close()

        stream = await MoonshineStream.create(
            transcriber=self._transcriber,
            session_id=session_id,
        )
        self._streams[session_id] = stream
        return stream

    async def remove_stream(self, session_id: str) -> None:
        stream = self._streams.pop(session_id, None)
        if stream is not None:
            await stream.close()

    async def close(self) -> None:
        for stream in list(self._streams.values()):
            await stream.close()
        self._streams.clear()


class MoonshineStream:
    """One caller's streaming ASR session."""

    def __init__(self, session_id: str, stream: Any) -> None:
        self.session_id = session_id
        self._stream = stream
        self._event_queue: asyncio.Queue[MoonshineTranscriptEvent] = asyncio.Queue()
        self._listener = _StreamingEventListener(self._event_queue)
        self._stream.add_listener(self._listener)
        self._closed = False
        self._start_time = time.time()
        logger.info("moonshine_stream_created", session_id=session_id)

    @classmethod
    async def create(
        cls,
        transcriber: Any,
        session_id: str,
    ) -> "MoonshineStream":
        def _make() -> "MoonshineStream":
            stream = transcriber.create_stream()
            stream.start()
            return cls(session_id=session_id, stream=stream)

        return await asyncio.to_thread(_make)

    async def add_audio(
        self,
        pcm_float32: np.ndarray,
        sample_rate: int = 16000,
    ) -> None:
        """Feed a chunk of mono PCM audio (float32) into the stream."""
        if self._closed:
            return
        audio_list = _to_list_float(pcm_float32)
        await asyncio.to_thread(self._stream.add_audio, audio_list, sample_rate)

    def events(self) -> asyncio.Queue[MoonshineTranscriptEvent]:
        """Return the queue that receives transcript events."""
        return self._event_queue

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await asyncio.to_thread(self._stream.stop)
        logger.info(
            "moonshine_stream_closed",
            session_id=self.session_id,
            duration_sec=round(time.time() - self._start_time, 1),
        )


# References
# [^King2026]: King, E., et al. (2026). Moonshine v2: Ergodic Streaming Encoder
#              ASR for Latency-Critical Speech Applications. arXiv:2602.12241.
# [^Moonshine2026]: Moonshine Voice documentation and benchmark tables, 2026.
