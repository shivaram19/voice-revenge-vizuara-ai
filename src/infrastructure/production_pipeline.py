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

Research Provenance:
    - Streaming STT saves 200–400 ms vs batch by overlapping ASR with
      speech [^22]
    - Turn-gap target <800 ms: callers perceive pauses >800 ms as
      unnatural and begin re-speaking [^29][^31][^SW1]
    - Barge-in latency budget <300 ms: detection-to-stop must be <200 ms
      for natural feel; >300 ms feels rude and disruptive [^4][^OG1][^FL1]
    - Deepgram Nova-3 streaming: ~80 ms time-to-first-partial [^23]
    - Echo cancellation settling time: 200–500 ms for acoustic echo
      cancellers per ITU-T G.168 [^ITU-G168]
    - Minimum inter-turn pause in human conversation: 600–1000 ms [^CP1]
    - Chunked audio sending: ~400 ms sub-chunks balance interruptibility
      (smaller = more responsive) against event-loop overhead [^BI1]
    - Blocking I/O in asyncio: must run in thread pool to prevent event-loop
      starvation [^PY1]
    - Deepgram endpointing=200 ms: fast conversational turn detection [^17]
    - Deepgram utterance_end_ms=1000 ms: captures trailing speech [^23]
    - Deepgram vad_events=true: enables SpeechStarted for barge-in [^28]
    - PII redact at source: "pci,ssn,numbers" prevents data leakage [^27]

Ref: ADR-009; ADR-012; Hexagonal Architecture (Cockburn 2005) [^42].
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

# Patience-aware tuning parameters — env-driven, calibrated by ADR-013 / DFS-007
# for Suryapet-parent demographic (slower speech, longer pauses, money-topic
# deliberation). Each defaults to the DFS-007 number; per-cohort overrides via env.
#
#   BARGE_IN_INITIAL_PROTECTION_MS: AEC settle + parent-processing guard [^ITU-G168]
#   BARGE_IN_COOLDOWN_MS:           min gap between barge-in triggers   [^CP1]
#   BARGE_IN_MIN_DURATION_MS:       distinguish backchannels from interrupts [^Heldner2010]
#   LLM_FILLER_AFTER_MS:            emit "one moment" if LLM exceeds this [^Frontiers2024]
#   IDLE_REPROMPT_MS:               gentle re-prompt after caller silence  [^Frontiers2024]
#   MAX_AGENT_TURN_WORDS:           per priyaṃ vada — keep agent turns short
#
#   AUDIO_CHUNK_MS: ~400 ms sub-chunks balance interruptibility vs. overhead [^BI1]
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


_INITIAL_PROTECTION_MS = _env_int("BARGE_IN_INITIAL_PROTECTION_MS", 800)
_BARGE_IN_COOLDOWN_MS = _env_int("BARGE_IN_COOLDOWN_MS", 1500)
_BARGE_IN_MIN_DURATION_MS = _env_int("BARGE_IN_MIN_DURATION_MS", 400)
_LLM_FILLER_AFTER_MS = _env_int("LLM_FILLER_AFTER_MS", 1500)
_IDLE_REPROMPT_MS = _env_int("IDLE_REPROMPT_MS", 6000)
_MAX_AGENT_TURN_WORDS = _env_int("MAX_AGENT_TURN_WORDS", 18)

_AUDIO_CHUNK_MS = 400          # Send audio in ~400 ms chunks [^BI1]
_AUDIO_BYTES_PER_MS = 8        # 8 kHz μ-law = 8 bytes/ms [^38]
_CHUNK_SIZE = _AUDIO_CHUNK_MS * _AUDIO_BYTES_PER_MS  # 3200 bytes

# Patience filler text (used when LLM exceeds _LLM_FILLER_AFTER_MS)
_FILLER_TEXT = "One moment please, sir."


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
        default_domain: Optional[str] = None,
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
        # ADR-013: default domain driven by env (DEFAULT_DOMAIN), not hard-coded.
        # The construction baseline was a project-history artefact; current
        # active deployment is Jaya High School / education.
        self.default_domain = (
            default_domain or os.getenv("DEFAULT_DOMAIN", "education")
        )
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
        # Greeting-completion gate: drop user transcripts that land before
        # the greeting playback finishes — prevents the agent from
        # responding to "Hello?" while the greeting is still being said
        # (DFS-007 §3 / ADR-013 graceful onboarding).
        self._greeting_done: Dict[str, bool] = {}
        # Adaptive turn-length state. We track the word count of each
        # caller utterance and converge our reply length onto theirs
        # (Communication Accommodation Theory: Giles 1991 / Pickering &
        # Garrod 2004). A 4-word caller gets a 4-word agent reply; a
        # 12-word caller gets up to 12. Floor 4 / ceiling MAX_AGENT_TURN_WORDS.
        self._caller_word_history: Dict[str, list[int]] = {}
        self._dynamic_max_words: Dict[str, int] = {}

        # Barge-in timing state
        self._tts_start_time: Dict[str, float] = {}   # When TTS started sending
        self._last_barge_in_time: Dict[str, float] = {}  # Last barge-in timestamp
        # Backchannel-vs-interrupt gate (ADR-013): time of speech_started, used
        # to require BARGE_IN_MIN_DURATION_MS of overlapping caller speech
        # before actually cancelling TTS.
        self._pending_barge_in_started_at: Dict[str, float] = {}
        self._last_caller_speech_at: Dict[str, float] = {}

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
        self._greeting_done[session_id] = False
        self._pending_barge_in_started_at[session_id] = 0.0
        self._last_caller_speech_at[session_id] = 0.0
        self._caller_word_history[session_id] = []
        self._dynamic_max_words[session_id] = _MAX_AGENT_TURN_WORDS

        # Start streaming STT connection — patience knobs are env-driven
        # per ADR-013/DFS-007. Suryapet defaults: endpointing 400 ms,
        # utterance-end 1800 ms (vs industry 200 / 1000).
        stt_config = StreamingSTTConfig(
            api_key=self.deepgram_api_key,
            language="en-IN",              # BCP-47 Indian English [^54]
            encoding="mulaw",              # Twilio Media Streams format [^43]
            sample_rate=8000,              # PSTN standard [^38]
            interim_results=True,          # Enable partial transcripts [^22]
            endpointing=_env_int("STT_ENDPOINTING_MS", 400),       # DFS-007
            utterance_end_ms=_env_int("STT_UTTERANCE_END_MS", 1800),  # DFS-007
            vad_events=True,               # SpeechStarted for barge-in [^28]
            redact="pci,ssn,numbers",      # PII redaction at source [^27]
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
            # Background task: send greeting; mark greeting_done when finished
            # so user transcripts arriving mid-greeting are dropped (ADR-013).
            asyncio.create_task(self._send_greeting(session_id, greeting_audio))
        else:
            # Without a send callback we can't gate on playback — assume done.
            self._greeting_done[session_id] = True

        return greeting_audio

    async def _send_greeting(self, session_id: str, audio: bytes) -> None:
        """Deliver the greeting and flip the greeting_done gate when done."""
        try:
            await self._send_with_tracking(session_id, audio)
        finally:
            self._greeting_done[session_id] = True
            logger.info("greeting_complete", session_id=session_id)

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
        self._greeting_done.pop(session_id, None)
        self._pending_barge_in_started_at.pop(session_id, None)
        self._last_caller_speech_at.pop(session_id, None)
        self._caller_word_history.pop(session_id, None)
        self._dynamic_max_words.pop(session_id, None)

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

        # Track last caller-speech moment for idle-reprompt + barge-in confirmation
        now_ms = time.time() * 1000
        self._last_caller_speech_at[session_id] = now_ms

        # ADR-013: confirm a *candidate* barge-in only when sustained caller
        # speech crosses BARGE_IN_MIN_DURATION_MS — distinguishes backchannels
        # ("haan", "hmm" <300 ms) from genuine interrupts (>500 ms).
        candidate_started = self._pending_barge_in_started_at.get(session_id, 0.0)
        if (
            self._is_speaking.get(session_id, False)
            and candidate_started > 0
            and (now_ms - candidate_started) >= _BARGE_IN_MIN_DURATION_MS
            and len(event.text) >= 3  # not just "uh"
        ):
            logger.info(
                "barge_in_confirmed",
                session_id=session_id,
                duration_ms=round(now_ms - candidate_started, 1),
                trigger_text=event.text[:60],
            )
            self._pending_barge_in_started_at[session_id] = 0.0
            self._handle_barge_in(session_id)

        # Accumulate final transcripts
        if event.is_final:
            self._final_buffers[session_id] = (
                self._final_buffers.get(session_id, "") + " " + event.text
            ).strip()
            logger.info(
                "stt_final",
                session_id=session_id,
                text=event.text,
                confidence=round(event.confidence, 3),
            )
            log_stt_transcript(
                session_id=session_id,
                transcript=event.text,
                is_final=True,
                confidence=event.confidence,
            )
            # Adaptive turn-length: feed each caller turn's word count
            # into the per-session history and re-derive the budget.
            self._adapt_turn_budget(session_id, event.text)

        # Trigger processing on speech_final or utterance_end
        if event.speech_final:
            buffer = self._final_buffers.get(session_id, "").strip()
            if buffer and len(buffer) >= 2:
                self._final_buffers[session_id] = ""
                # Drop the buffer if greeting is still in flight — prevents
                # the agent from "responding" to a confused "Hello?" the
                # parent uttered before they realized the agent was talking.
                if not self._greeting_done.get(session_id, False):
                    logger.info(
                        "transcript_dropped_during_greeting",
                        session_id=session_id,
                        text=buffer[:80],
                    )
                    return
                asyncio.create_task(self._process_utterance(session_id, buffer))

    def _on_speech_started(self, session_id: str) -> None:
        """
        User started speaking — *candidate* barge-in. Per ADR-013, do NOT cancel
        TTS yet: require BARGE_IN_MIN_DURATION_MS of sustained caller speech to
        distinguish a genuine interrupt from a backchannel ("haan", "hmm").
        Confirmation happens in `_on_transcript` when an actual transcript
        arrives. The protection / cooldown guards still apply here.
        """
        if not self._is_speaking.get(session_id, False):
            return

        now = time.time() * 1000  # ms
        start_ms = self._tts_start_time.get(session_id, 0) * 1000
        last_barge_ms = self._last_barge_in_time.get(session_id, 0) * 1000

        # Guard 1: initial protection — ignore barge-in for first N ms after TTS starts
        # Rationale: AEC needs 200–500 ms to converge [^ITU-G168]; Suryapet
        # parents need additional ~300 ms to register the opening words [DFS-007].
        if now - start_ms < _INITIAL_PROTECTION_MS:
            logger.debug(
                "barge_in_ignored_protection",
                session_id=session_id,
                elapsed_ms=round(now - start_ms, 1),
                threshold_ms=_INITIAL_PROTECTION_MS,
            )
            return

        # Guard 2: cooldown — ignore if we just handled a barge-in
        # Rationale: natural human turn-taking pauses are 600–1000 ms [^CP1]
        if now - last_barge_ms < _BARGE_IN_COOLDOWN_MS:
            logger.debug(
                "barge_in_ignored_cooldown",
                session_id=session_id,
                elapsed_ms=round(now - last_barge_ms, 1),
                threshold_ms=_BARGE_IN_COOLDOWN_MS,
            )
            return

        # Mark this as a *candidate* — do NOT cancel TTS yet. The confirmation
        # happens when an interim/final transcript actually arrives, at which
        # point we know the caller said something substantive (not a 200 ms
        # "haan" backchannel).
        self._pending_barge_in_started_at[session_id] = now
        logger.info(
            "barge_in_candidate",
            session_id=session_id,
            min_duration_ms=_BARGE_IN_MIN_DURATION_MS,
        )

    def _on_utterance_end(self, session_id: str) -> None:
        """Deepgram signaled utterance end — flush any remaining buffer."""
        buffer = self._final_buffers.get(session_id, "").strip()
        if buffer and len(buffer) >= 2:
            self._final_buffers[session_id] = ""
            if not self._greeting_done.get(session_id, False):
                logger.info(
                    "transcript_dropped_during_greeting",
                    session_id=session_id,
                    text=buffer[:80],
                )
                return
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
        filler_task: Optional[asyncio.Task] = None

        try:
            t0 = time.time()
            # ADR-013: schedule a patient filler if LLM exceeds the threshold.
            filler_task = asyncio.create_task(
                self._maybe_emit_filler(session_id, _LLM_FILLER_AFTER_MS)
            )

            with self.latency.measure("llm"):
                receptionist = self._session_receptionist.get(session_id)
                if receptionist is None:
                    return

                response_text = await receptionist.handle_transcript(session_id, transcript)
                llm_latency_ms = (time.time() - t0) * 1000

            # LLM finished — cancel pending filler if it didn't fire yet.
            if filler_task and not filler_task.done():
                filler_task.cancel()

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

                # If previously interrupted, set the prosody situation so the
                # voice softens — but do NOT inject a fixed acknowledgment
                # phrase. The system prompt instructs the LLM to produce a
                # context-appropriate, varied acknowledgment from real
                # conversation state. Prepending a hard-coded line (a) makes
                # the agent sound robotic on every interruption, and (b)
                # double-speaks when the LLM also adds its own. (DFS-007.)
                if self._was_interrupted.get(session_id, False):
                    situation = SpeechSituation.INTERRUPTED
                    self._was_interrupted[session_id] = False

                # ADR-013 + Communication Accommodation: trim cap per turn.
                # Exception — the SCENARIO OPENING (1st substantive agent
                # turn after greeting) always uses the full MAX_AGENT_TURN_WORDS
                # so the verified-record confirmation (e.g. "Aarav's fees are
                # paid in full") is heard intact. From turn 2 onward, the
                # dynamic budget mirrors the caller's recent word count and
                # keeps subsequent banter calibrated to their register.
                turn_index = self._turn_count.get(session_id, 0)
                if turn_index <= self._OPENING_TURN_INDEX:
                    budget = _MAX_AGENT_TURN_WORDS
                else:
                    budget = self._dynamic_max_words.get(
                        session_id, _MAX_AGENT_TURN_WORDS
                    )
                response_text = self._enforce_turn_length(response_text, budget)

                # Run blocking TTS HTTP call in thread pool — prevents event-loop
                # starvation that would stall WebSocket message handling [^PY1]
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
        Breaks audio into ~400 ms sub-chunks and checks `_was_interrupted`
        between each, yielding control to the event loop so barge-in
        cancellation has an await point at which to take effect [^BI1][^PY1].
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
                # Yield control — critical for task cancellation [^PY1]
                await asyncio.sleep(0.001)

        except asyncio.CancelledError:
            logger.info("tts_send_cancelled", session_id=session_id)
            raise
        finally:
            self._is_speaking[session_id] = False

    # ------------------------------------------------------------------
    # Patience helpers (ADR-013 / DFS-007)
    # ------------------------------------------------------------------

    async def _maybe_emit_filler(self, session_id: str, after_ms: int) -> None:
        """
        Wait `after_ms` and, if the LLM is still in flight and the agent has
        nothing playing, emit a brief filler so the line is never silent.
        Cancelled normally when the LLM finishes in time.
        """
        try:
            await asyncio.sleep(after_ms / 1000.0)
        except asyncio.CancelledError:
            return

        # Only emit if still processing and not currently speaking.
        if not self._is_processing.get(session_id, False):
            return
        if self._is_speaking.get(session_id, False):
            return

        send_cb = self._send_callbacks.get(session_id)
        if not send_cb:
            return

        logger.info(
            "filler_emitted",
            session_id=session_id,
            after_ms=after_ms,
            text=_FILLER_TEXT,
        )
        try:
            audio = await self._synthesize_to_ulaw(
                _FILLER_TEXT, emotion_tone=None, situation=SpeechSituation.DEFAULT
            )
            self._is_speaking[session_id] = True
            self._tts_start_time[session_id] = time.time()
            await self._send_with_tracking(session_id, audio)
        except Exception as exc:
            logger.warning("filler_failed", session_id=session_id, error=str(exc))

    # Budget floor: anything shorter than 6 words risks clipping
    # meaningful content (verified-record confirmations, scenario
    # closings). Per Yngve 1970 the minimum acknowledgment-plus-content
    # unit is ~4 words; we add 2 to allow for honorifics ("sir") and a
    # short content fragment.
    _BUDGET_FLOOR = 6
    # The scenario *opening* turn (1st substantive agent reply after the
    # parent's consent) MUST convey the verified-record confirmation in
    # full — that is the *reason for the call*. Adapting the opening to
    # match a 1-word "Yes" caller would clip the only content the parent
    # actually needs to hear. So the opening turn always uses the full
    # MAX_AGENT_TURN_WORDS; the budget mirror kicks in from turn 2.
    _OPENING_TURN_INDEX = 0  # before any LLM turn has run

    def _adapt_turn_budget(self, session_id: str, caller_text: str) -> None:
        """
        Communication Accommodation: converge agent turn length onto the
        caller's. Each caller utterance contributes its word count to a
        per-session history; the budget is the mean of the most recent
        two caller turns, clipped to [_BUDGET_FLOOR, MAX_AGENT_TURN_WORDS].

        Why mean-of-2 (not last only): a single 1-word "Yes" should not
        permanently lock us at the floor; a sliding window lets the
        budget breathe with the caller's actual register.
        """
        if not caller_text:
            return
        words = len(caller_text.split())
        history = self._caller_word_history.setdefault(session_id, [])
        history.append(words)
        recent = history[-2:]
        avg = sum(recent) / len(recent)
        budget = max(self._BUDGET_FLOOR, min(_MAX_AGENT_TURN_WORDS, int(round(avg))))
        prev = self._dynamic_max_words.get(session_id, _MAX_AGENT_TURN_WORDS)
        self._dynamic_max_words[session_id] = budget
        if budget != prev:
            logger.info(
                "turn_budget_calibrated",
                session_id=session_id,
                caller_words=words,
                recent_window=recent,
                dynamic_max_words=budget,
                previous_max_words=prev,
            )

    @staticmethod
    def _enforce_turn_length(text: str, max_words: int) -> str:
        """
        Trim agent response to ~max_words at the nearest sentence boundary.
        Keeps the first sentence(s) whose total word count ≤ max_words; if
        even the first sentence exceeds the limit, hard-cap on word count.
        """
        if not text:
            return text
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        kept: list[str] = []
        word_count = 0
        for sent in sentences:
            n = len(sent.split())
            if not kept:
                # Always keep the first sentence; hard-cap if over budget.
                if n > max_words * 1.5:
                    return " ".join(sent.split()[: max_words])
                kept.append(sent)
                word_count = n
                continue
            if word_count + n > max_words:
                break
            kept.append(sent)
            word_count += n
        return " ".join(kept)

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
        """
        Synthesize text with emotion-mapped prosody and situational SSML.
        Runs blocking TTS HTTP call in a thread pool to prevent event loop
        blocking [^PY1]. Twilio Media Streams requires the event loop to
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
        # Run blocking HTTP call in thread pool — critical for asyncio [^PY1]
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
# [^4]: Deepgram / ElevenLabs. (2026). Barge-In & Turn-Taking Guide.
#        Target: <100 ms detection-to-stop for natural interruptions.
# [^17]: Deepgram. (2024). Configure Endpointing and Interim Results.
# [^22]: Gladia. (2025). Concurrent pipelines for voice AI.
# [^23]: Edesy. (2026). Deepgram Nova-3 STT for Voice Agents.
# [^27]: Deepgram. (2026). PII Redaction Developer Guide.
# [^28]: Deepgram. (2024). VAD Events documentation.
# [^29]: AssemblyAI. (2026). Phone-based voice agent guide.
# [^31]: TeamDay AI. (2026). Voice AI Architecture Guide.
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation.
# [^42]: Cockburn, A. (2005). Hexagonal Architecture.
# [^43]: Twilio. (2024). Media Streams API Documentation.
# [^54]: Deepgram. Language BCP-47 tags.
# [^94]: Martin, R. C. (2002). Agile Software Development.
# [^BI1]: AVA-AI / Hamming AI. (2026). Barge-in configuration: protection,
#          cooldown, chunking. 400 ms chunks balance interruptibility vs overhead.
# [^PY1]: Python asyncio docs. (2024). Running blocking code in executor threads.
#          docs.python.org/3/library/asyncio-eventloop.html#executing-code-in-thread-or-process-pools
# [^ITU-G168]: ITU-T. (2015). G.168: Digital network echo cancellers.
#               AEC convergence time: 200–500 ms for typical acoustic environments.
# [^CP1]: Sacks, H., Schegloff, E. A., & Jefferson, G. (1974). A Simplest
#         Systematics for the Organization of Turn-Taking for Conversation.
#         Language, 50(4), 696–735.  Minimum inter-turn gap: ~600 ms telephone.
# [^OG1]: Orga AI. (2026). Barge-in for Voice Agents: What It Is & How to
#          Implement It Properly. orga-ai.com/blog/blog-barge-in-voice-agents-guide
# [^FL1]: Famulor. (2026). The Art of Listening: Turn Detection and Interruption
#          Handling. famulor.io/blog/the-art-of-listening-mastering-turn-detection
#          Barge-in latency >300 ms perceived as unnatural.
# [^SW1]: SignalWire. (2026). What Twenty Years of Voice Infrastructure Taught Me.
#          signalwire.com/blogs/ceo/twenty-years-of-voice-infrastructure
#          Turn-gap >800 ms feels unnatural; >2 s caller assumes system is broken.
