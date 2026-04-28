"""
Production Live AI Pipeline (Streaming)
========================================
Real-time STT → LLM → TTS pipeline using Deepgram streaming WebSocket.
Eliminates batch WAV-file latency; actively transcribes while user speaks.

Architecture:
    Twilio μ-law 8kHz ──► StreamingDeepgramSTT (WebSocket)
                              │
                              ▼
                        TranscriptEvent (is_final + speech_final)
                              │
                              ▼
                        Azure OpenAI GPT-4o-mini (tool calling)
                              │
                              ▼
                        Deepgram Aura TTS
                              │
                              ▼
                        Async callback ──► Twilio WebSocket

Research:
    - Streaming STT saves 200–400ms vs batch [^22]
    - Turn-gap target: <800ms [^29][^31]
    - Barge-in latency budget: <300ms [^4]
    - Deepgram Nova-3 streaming: ~80ms TTFP [^23]
    - Barge-in config: initial_protection=500ms, cooldown=1000ms [^BI1]

Ref: ADR-009; Hexagonal Architecture (Cockburn 2005) [^42].
"""

from __future__ import annotations

import os
import sys
import base64
import asyncio
import time
import wave
import io
import re
from pathlib import Path
from typing import Optional, Dict, Any, Callable

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.telephony.gateway import TelephonyGateway
from src.telephony._audio_compat import ratecv, lin2ulaw
from src.receptionist.service import Receptionist, CallSession

from src.domains.registry import DomainRegistry
from src.domains.router import DomainRouter
from src.infrastructure.interfaces import DomainPort

from src.streaming.streaming_stt_deepgram import (
    StreamingDeepgramSTT,
    StreamingSTTConfig,
    TranscriptEvent,
)
from src.infrastructure.latency_tracker import LatencyTracker
from src.emotion.tts_prosody import SpeechSituation
from src.infrastructure.logging_config import get_logger
from src.infrastructure.telemetry import (
    log_stt_transcript,
    log_llm_response,
    log_tts_synthesis,
    log_barge_in,
    log_exception,
    log_voice_event,
)

logger = get_logger("pipeline.production")

# Barge-in tuning parameters [^BI1]
_INITIAL_PROTECTION_MS = 500   # Ignore barge-in for 500ms after TTS starts (echo guard)
_BARGE_IN_COOLDOWN_MS = 1000   # Min ms between barge-in triggers
_AUDIO_CHUNK_MS = 400          # Send audio in ~400ms chunks for interruptibility
_AUDIO_BYTES_PER_MS = 8        # 8 kHz μ-law = 8 bytes/ms
_CHUNK_SIZE = _AUDIO_CHUNK_MS * _AUDIO_BYTES_PER_MS  # 3200 bytes


# ---------------------------------------------------------------------------
# Production Pipeline Orchestrator (Streaming)
# ---------------------------------------------------------------------------

class ProductionPipeline:
    """
    Streaming pipeline: Deepgram STT → Azure OpenAI LLM → Deepgram Aura TTS.
    Event-driven: audio flows in via on_media_chunk; responses flow out
    via the send_callback registered in on_call_start.
    """

    def __init__(
        self,
        domain_registry: DomainRegistry,
        domain_router: DomainRouter,
        gateway: TelephonyGateway,
        stt: Any = None,          # Kept for DI compat; ignored in streaming mode
        tts: Any = None,
        prosody_mapper: Any = None,
        llm_factory: Callable = None,
        default_domain: str = "construction",
        deepgram_api_key: Optional[str] = None,
    ):
        # DIP: dependencies injected from composition root [^94]
        self.gateway = gateway
        self.stt_legacy = stt           # Legacy batch STT (unused in streaming)
        self.tts = tts
        self.prosody_mapper = prosody_mapper
        self.llm_factory = llm_factory
        self.domain_registry = domain_registry
        self.domain_router = domain_router
        self.default_domain = default_domain
        self.deepgram_api_key = deepgram_api_key or os.getenv("DEEPGRAM_API_KEY", "")

        # Per-session state
        self._receptionists: Dict[str, Receptionist] = {}
        self._session_receptionist: Dict[str, Receptionist] = {}
        self._streaming_stts: Dict[str, StreamingDeepgramSTT] = {}
        self._send_callbacks: Dict[str, Callable[[bytes], Any]] = {}
        self._tts_tasks: Dict[str, asyncio.Task] = {}
        self._final_buffers: Dict[str, str] = {}
        self._is_speaking: Dict[str, bool] = {}       # AI currently speaking
        self._is_processing: Dict[str, bool] = {}     # LLM+TTS in flight
        self._was_interrupted: Dict[str, bool] = {}   # Barge-in detected
        self._turn_count: Dict[str, int] = {}         # Turns completed

        # Barge-in timing state
        self._tts_start_time: Dict[str, float] = {}   # When TTS started sending
        self._last_barge_in_time: Dict[str, float] = {}  # Last barge-in timestamp

        # Latency tracking
        self.latency = LatencyTracker()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def on_call_start(
        self,
        session_id: str,
        caller: str,
        called: str,
        domain_id: Optional[str] = None,
        send_callback: Optional[Callable[[bytes], Any]] = None,
    ) -> bytes:
        """
        Initialize a call session.
        Returns greeting audio bytes (legacy compat).
        If send_callback is provided, greeting is also sent asynchronously.
        """
        if domain_id:
            resolved_id = domain_id
        elif called is None:
            resolved_id = self.default_domain
        else:
            domain = self.domain_router.resolve(phone_number=called)
            resolved_id = domain.domain_id if domain is not None else self.default_domain

        receptionist = self._get_or_create_receptionist(resolved_id)
        self._session_receptionist[session_id] = receptionist
        self._send_callbacks[session_id] = send_callback
        self._final_buffers[session_id] = ""
        self._is_speaking[session_id] = False
        self._is_processing[session_id] = False
        self._was_interrupted[session_id] = False
        self._turn_count[session_id] = 0
        self._tts_start_time[session_id] = 0.0
        self._last_barge_in_time[session_id] = 0.0

        # Start streaming STT connection
        stt_config = StreamingSTTConfig(
            api_key=self.deepgram_api_key,
            language="en-IN",
            encoding="mulaw",
            sample_rate=8000,
            interim_results=True,
            endpointing=200,
            utterance_end_ms=1000,
            vad_events=True,
            redact="pci,ssn,numbers",  # PII redaction at source [^27]
        )
        stt = StreamingDeepgramSTT(config=stt_config)
        await stt.connect(
            on_transcript=lambda ev: self._on_transcript(session_id, ev),
            on_speech_started=lambda: self._on_speech_started(session_id),
            on_utterance_end=lambda: self._on_utterance_end(session_id),
            on_error=lambda msg: logger.error("stt_error", session_id=session_id, error=msg),
        )
        self._streaming_stts[session_id] = stt

        # Generate greeting
        with self.latency.measure("greeting"):
            greeting_text = await receptionist.handle_call_start(session_id, caller, called)
            greeting_audio = await self._synthesize_to_ulaw(greeting_text, emotion_tone=None)

        if send_callback:
            self._is_speaking[session_id] = True
            self._tts_start_time[session_id] = time.time()
            asyncio.create_task(self._send_with_tracking(session_id, greeting_audio))

        return greeting_audio

    async def on_media_chunk(self, session_id: str, payload_b64: str) -> Optional[bytes]:
        """
        Feed inbound audio into the streaming STT pipeline.
        With streaming, responses are pushed via callback, not returned.
        Returns None to maintain legacy interface.
        """
        stt = self._streaming_stts.get(session_id)
        if stt is None:
            return None

        mulaw_bytes = base64.b64decode(payload_b64)
        await stt.send_audio(mulaw_bytes)
        return None

    async def on_call_end(self, session_id: str) -> Optional[CallSession]:
        """Finalize session and cleanup."""
        stt = self._streaming_stts.pop(session_id, None)
        if stt:
            await stt.close()

        self._send_callbacks.pop(session_id, None)
        self._final_buffers.pop(session_id, None)
        self._is_speaking.pop(session_id, None)
        self._is_processing.pop(session_id, None)
        self._was_interrupted.pop(session_id, None)
        self._turn_count.pop(session_id, None)
        self._tts_start_time.pop(session_id, None)
        self._last_barge_in_time.pop(session_id, None)

        # Cancel any in-flight TTS
        task = self._tts_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        receptionist = self._session_receptionist.pop(session_id, None)
        if receptionist is None:
            return None
        try:
            return await receptionist.handle_call_end(session_id)
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Streaming STT callbacks
    # ------------------------------------------------------------------

    def _on_transcript(self, session_id: str, event: TranscriptEvent) -> None:
        """Handle a transcript event from Deepgram streaming."""
        if not event.text:
            return

        # Accumulate final transcripts
        if event.is_final:
            self._final_buffers[session_id] = (
                self._final_buffers.get(session_id, "") + " " + event.text
            ).strip()
            logger.info("stt_final", session_id=session_id, text=event.text)
            log_stt_transcript(
                session_id=session_id,
                transcript=event.text,
                is_final=True,
                confidence=event.confidence,
            )

        # Trigger processing on speech_final or utterance_end
        if event.speech_final:
            buffer = self._final_buffers.get(session_id, "").strip()
            if buffer and len(buffer) >= 2:
                self._final_buffers[session_id] = ""
                asyncio.create_task(self._process_utterance(session_id, buffer))

    def _on_speech_started(self, session_id: str) -> None:
        """
        User started speaking — detect barge-in if AI is currently speaking.
        Guards against self-echo (initial_protection) and rapid re-trigger (cooldown).
        """
        if not self._is_speaking.get(session_id, False):
            return

        now = time.time() * 1000  # ms
        start_ms = self._tts_start_time.get(session_id, 0) * 1000
        last_barge_ms = self._last_barge_in_time.get(session_id, 0) * 1000

        # Guard 1: initial protection — ignore barge-in for first N ms after TTS starts
        if now - start_ms < _INITIAL_PROTECTION_MS:
            logger.debug(
                "barge_in_ignored_protection",
                session_id=session_id,
                elapsed_ms=round(now - start_ms, 1),
            )
            return

        # Guard 2: cooldown — ignore if we just handled a barge-in
        if now - last_barge_ms < _BARGE_IN_COOLDOWN_MS:
            logger.debug(
                "barge_in_ignored_cooldown",
                session_id=session_id,
                elapsed_ms=round(now - last_barge_ms, 1),
            )
            return

        logger.info("barge_in_detected", session_id=session_id)
        self._handle_barge_in(session_id)

    def _on_utterance_end(self, session_id: str) -> None:
        """Deepgram signaled utterance end — flush any remaining buffer."""
        buffer = self._final_buffers.get(session_id, "").strip()
        if buffer and len(buffer) >= 2:
            self._final_buffers[session_id] = ""
            asyncio.create_task(self._process_utterance(session_id, buffer))

    # ------------------------------------------------------------------
    # Barge-in handling
    # ------------------------------------------------------------------

    def _handle_barge_in(self, session_id: str) -> None:
        """User interrupted the AI. Yield with vinaya (humility)."""
        self._is_speaking[session_id] = False
        self._was_interrupted[session_id] = True
        self._last_barge_in_time[session_id] = time.time()

        task = self._tts_tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            logger.info("barge_in_tts_cancelled", session_id=session_id)
            log_barge_in(session_id)

        # Clear any pending processing flag so next utterance can proceed
        self._is_processing[session_id] = False

    # ------------------------------------------------------------------
    # Utterance processing
    # ------------------------------------------------------------------

    async def _process_utterance(self, session_id: str, transcript: str) -> None:
        """Process a completed user utterance: LLM → TTS → send audio."""
        if self._is_processing.get(session_id, False):
            logger.warning(
                "utterance_dropped_concurrent",
                session_id=session_id,
                transcript=transcript,
            )
            return

        self._is_processing[session_id] = True
        send_cb = self._send_callbacks.get(session_id)
        llm_latency_ms = 0.0
        tts_latency_ms = 0.0

        try:
            t0 = time.time()
            with self.latency.measure("llm"):
                receptionist = self._session_receptionist.get(session_id)
                if receptionist is None:
                    return

                response_text = await receptionist.handle_transcript(session_id, transcript)
                llm_latency_ms = (time.time() - t0) * 1000

            logger.info(
                "llm_response",
                session_id=session_id,
                response=response_text[:200],
                latency_ms=round(llm_latency_ms, 1),
            )
            log_llm_response(
                session_id=session_id,
                response_text=response_text,
                latency_ms=llm_latency_ms,
                model="gpt-4o-mini",
            )

            t1 = time.time()
            with self.latency.measure("tts"):
                from src.emotion.profile import EmotionalTone
                emotion_tone = None
                emotion_state = receptionist.get_emotion_state(session_id)
                if emotion_state:
                    emotion_tone = emotion_state.latest_target_tone
                    if emotion_state.should_offer_human:
                        response_text += (
                            " Would you like me to connect you with a human representative?"
                        )

                # Determine situation based on context
                situation = self._determine_situation(session_id, response_text)

                # If previously interrupted, prepend graceful acknowledgment
                if self._was_interrupted.get(session_id, False):
                    response_text = (
                        "I shall pause. Please, tell me what is on your mind. "
                        + response_text
                    )
                    situation = SpeechSituation.INTERRUPTED
                    self._was_interrupted[session_id] = False

                response_audio = await self._synthesize_to_ulaw(
                    response_text, emotion_tone, situation
                )
                tts_latency_ms = (time.time() - t1) * 1000

            log_tts_synthesis(
                session_id=session_id,
                voice_model=getattr(self, "_last_voice", "unknown"),
                latency_ms=tts_latency_ms,
                text_length=len(response_text),
            )
            self._turn_count[session_id] = self._turn_count.get(session_id, 0) + 1

            if send_cb:
                self._is_speaking[session_id] = True
                self._tts_start_time[session_id] = time.time()
                task = asyncio.create_task(
                    self._send_with_tracking(session_id, response_audio)
                )
                self._tts_tasks[session_id] = task
            else:
                logger.warning("no_send_callback", session_id=session_id)

        except Exception as e:
            logger.error(
                "utterance_processing_error",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            log_exception(e, session_id, {"stage": "process_utterance", "transcript": transcript})
        finally:
            self._is_processing[session_id] = False

    async def _send_with_tracking(self, session_id: str, audio: bytes) -> None:
        """
        Send audio via callback in interruptible chunks.
        Breaks audio into ~400ms sub-chunks and checks `_was_interrupted`
        between each, yielding control to the event loop so barge-in
        cancellation has an await point at which to take effect [^BI1].
        """
        send_cb = self._send_callbacks.get(session_id)
        if not send_cb:
            self._is_speaking[session_id] = False
            return

        try:
            for i in range(0, len(audio), _CHUNK_SIZE):
                # Check if barge-in occurred since last chunk
                if self._was_interrupted.get(session_id, False):
                    logger.info(
                        "audio_send_interrupted",
                        session_id=session_id,
                        bytes_sent=i,
                        total_bytes=len(audio),
                    )
                    break

                chunk = audio[i : i + _CHUNK_SIZE]
                await send_cb(chunk)
                # Yield control — critical for task cancellation [^BI1]
                await asyncio.sleep(0.001)

        except asyncio.CancelledError:
            logger.info("tts_send_cancelled", session_id=session_id)
            raise
        finally:
            self._is_speaking[session_id] = False

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def _determine_situation(self, session_id: str, response_text: str) -> SpeechSituation:
        """Determine speech situation based on conversation context (Kāla-Deśa-Pātra)."""
        turn = self._turn_count.get(session_id, 0)
        text_lower = response_text.lower()

        # First turn = greeting
        if turn == 0:
            return SpeechSituation.GREETING

        # Closing phrases
        if any(p in text_lower for p in ["goodbye", "good bye", "thank you for calling", "have a good"]):
            return SpeechSituation.CLOSING

        # Fee-related = compassionate
        if any(p in text_lower for p in ["fee", "rupees", "₹", "payment", "installment", "afford"]):
            return SpeechSituation.COMPASSIONATE

        # Course explanation = instruction
        if any(p in text_lower for p in ["course", "weeks", "program", "syllabus", "batch"]):
            return SpeechSituation.INSTRUCTION

        # Enthusiasm for ANN / technology
        if any(p in text_lower for p in ["neural network", "ai", "coding", "project", "exciting"]):
            return SpeechSituation.ENTHUSIASTIC

        return SpeechSituation.DEFAULT

    async def _synthesize_to_ulaw(
        self, text: str, emotion_tone=None, situation: SpeechSituation = None
    ) -> bytes:
        """Synthesize text with emotion-mapped prosody and situational SSML.
        Runs blocking TTS HTTP call in a thread pool to prevent event loop
        blocking [^AS1]. Twilio Media Streams requires the event loop to
        remain responsive for incoming audio chunks [^43].
        """
        from src.emotion.profile import EmotionalTone
        target = emotion_tone or EmotionalTone.CALM
        sit = situation or SpeechSituation.DEFAULT

        adapted_text, voice_model, use_ssml = self.prosody_mapper.map(
            text, target, situation=sit
        )
        # Store for telemetry
        self._last_voice = voice_model
        # Run blocking HTTP call in thread pool — critical for asyncio [^AS1]
        pcm_24k = await asyncio.to_thread(
            self.tts.synthesize, adapted_text, model=voice_model, ssml=use_ssml
        )

        wav_buffer = io.BytesIO(pcm_24k)
        with wave.open(wav_buffer, "rb") as w:
            pcm_24k_raw = w.readframes(w.getnframes())

        pcm_8k, _ = ratecv(pcm_24k_raw, 2, 1, 24000, 8000, None)
        mulaw = lin2ulaw(pcm_8k, 2)
        return mulaw

    # ------------------------------------------------------------------
    # Receptionist factory
    # ------------------------------------------------------------------

    def _get_or_create_receptionist(self, domain_id: str) -> Receptionist:
        if domain_id in self._receptionists:
            return self._receptionists[domain_id]

        domain = self.domain_registry.get(domain_id)
        if domain is None:
            raise ValueError(f"Unknown domain: {domain_id}")

        llm = self.llm_factory()
        receptionist = domain.create_receptionist(llm_client=llm, tts_provider=None)
        self._receptionists[domain_id] = receptionist
        return receptionist


# References
# [^4]: Deepgram. (2026). Barge-In & Turn-Taking Guide.
# [^22]: Gladia. (2025). Concurrent pipelines for voice AI.
# [^23]: Edesy. (2026). Deepgram Nova-3 STT for Voice Agents.
# [^27]: Deepgram. (2026). PII Redaction Developer Guide.
# [^29]: AssemblyAI. (2026). Phone-based voice agent guide.
# [^31]: TeamDay AI. (2026). Voice AI Architecture Guide.
# [^42]: Cockburn, A. (2005). Hexagonal Architecture.
# [^94]: Martin, R. C. (2002). Agile Software Development.
# [^AS1]: Python asyncio docs. (2024). Running blocking code in executor threads.
#          https://docs.python.org/3/library/asyncio-eventloop.html#executing-code-in-thread-or-process-pools
# [^BI1]: AVA-AI / Hamming AI. (2026). Barge-in configuration: protection, cooldown, chunking.
