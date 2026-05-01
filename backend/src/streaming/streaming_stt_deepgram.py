"""
Streaming Deepgram STT Client
==============================
Real-time speech-to-text via Deepgram Nova-3 streaming WebSocket.
Sends μ-law audio chunks as they arrive from Twilio; receives transcripts,
endpointing events, and VAD events in real-time.

Research Provenance:
    - Deepgram streaming Nova-3: ~80ms time-to-first-partial [^23]
    - Encoding: mulaw, Sample rate: 8000 for Twilio PSTN [^43][^38]
    - endpointing=200: fast conversational turn detection [^17]
    - utterance_end_ms=1000: captures trailing speech [^23]
    - vad_events=true: enables barge-in detection via speech_started [^28]
    - interim_results=true: allows downstream speculative processing [^22]

Ref: Deepgram. (2024). Streaming API Documentation.
     https://developers.deepgram.com/docs/getting-started-with-pre-recorded-audio
"""

from __future__ import annotations

import json
import asyncio
from typing import Optional, Callable
from dataclasses import dataclass, field

import websockets


@dataclass
class StreamingSTTConfig:
    """Configuration for Deepgram streaming STT."""
    api_key: str
    model: str = "nova-3"
    language: str = "en-IN"          # BCP-47 tag for Indian English [^54]
    encoding: str = "mulaw"          # Twilio Media Streams format [^43]
    sample_rate: int = 8000          # PSTN standard [^38]
    interim_results: bool = True     # Enable partial transcripts [^22]
    punctuate: bool = True
    smart_format: bool = True
    endpointing: int = 200           # ms silence for conversational endpointing [^17]
    utterance_end_ms: int = 1000     # ms trailing capture [^23]
    vad_events: bool = True          # Enable SpeechStarted events for barge-in [^28]
    filler_words: bool = True        # Keep "um", "uh" for naturalness
    redact: str = ""                  # PII redaction: "pci,ssn,numbers" [^27]


@dataclass
class TranscriptEvent:
    """A transcript event from Deepgram streaming."""
    text: str
    is_final: bool = False
    speech_final: bool = False
    confidence: float = 0.0
    words: list = field(default_factory=list)


class StreamingDeepgramSTT:
    """
    Async streaming STT client for Deepgram Nova-3.

    Usage:
        stt = StreamingDeepgramSTT(config)
        await stt.connect(on_transcript=..., on_speech_started=...)
        await stt.send_audio(mulaw_chunk)
        ...
        await stt.close()
    """

    def __init__(self, config: Optional[StreamingSTTConfig] = None):
        self.config = config or StreamingSTTConfig(api_key="")
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._connected = False
        self._closed = False

        # Callbacks (set via connect())
        self._on_transcript: Optional[Callable[[TranscriptEvent], None]] = None
        self._on_speech_started: Optional[Callable[[], None]] = None
        self._on_speech_ended: Optional[Callable[[], None]] = None
        self._on_utterance_end: Optional[Callable[[], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        # Internal state
        self._pending_interim: str = ""
        self._final_buffer: str = ""

        # Logging
        from src.infrastructure.logging_config import get_logger
        self._logger = get_logger("streaming.stt")

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self,
        on_transcript: Optional[Callable[[TranscriptEvent], None]] = None,
        on_speech_started: Optional[Callable[[], None]] = None,
        on_speech_ended: Optional[Callable[[], None]] = None,
        on_utterance_end: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Open WebSocket connection to Deepgram streaming endpoint."""
        if self._connected:
            return

        self._on_transcript = on_transcript
        self._on_speech_started = on_speech_started
        self._on_speech_ended = on_speech_ended
        self._on_utterance_end = on_utterance_end
        self._on_error = on_error

        url = self._build_url()
        headers = {"Authorization": f"Token {self.config.api_key}"}

        try:
            self._ws = await websockets.connect(url, additional_headers=headers)
            self._connected = True
            self._closed = False
            self._receive_task = asyncio.create_task(
                self._receive_loop(), name="deepgram-receive"
            )
            self._logger.info("deepgram_connected")
        except Exception as e:
            self._logger.error("deepgram_connection_failed", error=str(e))
            if self._on_error:
                self._on_error(str(e))
            raise

    async def close(self) -> None:
        """Gracefully close the WebSocket connection."""
        self._closed = True
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        self._connected = False
        self._logger.info("deepgram_disconnected")

    # ------------------------------------------------------------------
    # Audio input
    # ------------------------------------------------------------------

    async def send_audio(self, mulaw_bytes: bytes) -> None:
        """Send a μ-law audio chunk to Deepgram."""
        if not self._connected or self._ws is None:
            return
        try:
            await self._ws.send(mulaw_bytes)
        except websockets.exceptions.ConnectionClosed:
            self._connected = False
            if self._on_error:
                self._on_error("WebSocket closed unexpectedly")
        except Exception as e:
            if self._on_error:
                self._on_error(f"Send error: {e}")

    # ------------------------------------------------------------------
    # Receive loop
    # ------------------------------------------------------------------

    async def _receive_loop(self) -> None:
        """Background task: receive and dispatch Deepgram events."""
        while not self._closed and self._ws:
            try:
                msg = await self._ws.recv()
                if isinstance(msg, str):
                    self._handle_text_message(msg)
            except websockets.exceptions.ConnectionClosedOK:
                break
            except websockets.exceptions.ConnectionClosedError as e:
                if self._on_error:
                    self._on_error(f"WebSocket closed: {e}")
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._on_error:
                    self._on_error(f"Receive error: {e}")

    def _handle_text_message(self, raw: str) -> None:
        """Parse and dispatch a JSON message from Deepgram."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "")

        if msg_type == "Results":
            self._handle_results(data)
        elif msg_type == "SpeechStarted":
            if self._on_speech_started:
                self._on_speech_started()
        elif msg_type == "SpeechEnded":
            if self._on_speech_ended:
                self._on_speech_ended()
        elif msg_type == "UtteranceEnd":
            if self._on_utterance_end:
                self._on_utterance_end()
        elif msg_type == "Error":
            err = data.get("description", "Unknown Deepgram error")
            self._logger.error("deepgram_error", description=err)
            if self._on_error:
                self._on_error(err)

    def _handle_results(self, data: dict) -> None:
        """Handle a transcript Results event."""
        channel = data.get("channel", {})
        alt = channel.get("alternative", {})
        if not alt:
            # Pre-API v2 format
            channel = data.get("channel", {})
            alternatives = channel.get("alternatives", [{}])
            alt = alternatives[0] if alternatives else {}

        transcript = alt.get("transcript", "").strip()
        if not transcript:
            return

        is_final = data.get("is_final", False)
        speech_final = data.get("speech_final", False)
        confidence = alt.get("confidence", 0.0)
        words = alt.get("words", [])

        event = TranscriptEvent(
            text=transcript,
            is_final=is_final,
            speech_final=speech_final,
            confidence=confidence,
            words=words,
        )

        if self._on_transcript:
            self._on_transcript(event)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_url(self) -> str:
        """Build the Deepgram streaming WebSocket URL with query params."""
        base = "wss://api.deepgram.com/v1/listen"
        params = {
            "model": self.config.model,
            "language": self.config.language,
            "encoding": self.config.encoding,
            "sample_rate": self.config.sample_rate,
            "interim_results": str(self.config.interim_results).lower(),
            "punctuate": str(self.config.punctuate).lower(),
            "smart_format": str(self.config.smart_format).lower(),
            "endpointing": self.config.endpointing,
            "utterance_end_ms": self.config.utterance_end_ms,
            "vad_events": str(self.config.vad_events).lower(),
            "filler_words": str(self.config.filler_words).lower(),
        }
        query_parts = [f"{k}={v}" for k, v in params.items()]
        # Deepgram requires multiple `redact` query params for multiple types;
        # comma-separated values return HTTP 400 [^DG1].
        if self.config.redact:
            for redact_type in self.config.redact.split(","):
                redact_type = redact_type.strip()
                if redact_type:
                    query_parts.append(f"redact={redact_type}")
        query = "&".join(query_parts)
        return f"{base}?{query}"


# References
# [^17]: Deepgram. (2024). Configure Endpointing and Interim Results.
# [^22]: Gladia. (2025). Concurrent pipelines for voice AI.
# [^23]: Edesy. (2026). Deepgram Nova-3 STT for Voice Agents.
# [^28]: Deepgram. (2024). VAD Events documentation.
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation.
# [^DG1]: Deepgram. (2024). Streaming API Documentation — Query Parameters.
#         `redact` must be passed as multiple query parameters (`redact=pci&redact=ssn`);
#         comma-separated values (`redact=pci,ssn`) return HTTP 400.
#         Confirmed via live API testing on 2026-04-28.
# [^43]: Twilio. (2024). Media Streams API Documentation.
# [^54]: Deepgram. Language BCP-47 tags.
