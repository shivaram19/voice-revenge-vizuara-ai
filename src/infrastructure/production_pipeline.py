"""
Production Live AI Pipeline
============================
Cloud-only STT → LLM → TTS pipeline for production deployments.
Uses Deepgram Nova-3 STT, Azure OpenAI GPT-4o-mini LLM, and
Deepgram Aura TTS. No local models required.

Research Provenance:
    - Cloud APIs eliminate GPU/CPU compute bottlenecks on the
      agent controller, enabling higher concurrent call density
      on small containers [^25][^69][^70].
    - Deepgram Nova-3 + Aura provide end-to-end voice processing
      with <500ms combined latency [^61][^70].
    - Azure OpenAI GPT-4o-mini achieves <200ms TTFT for
      tool-calling workloads [^69].
    - For 10-20 concurrent calls, cloud API cost ($0.02/minute
      combined) is far below the cost of a GPU VM ($500+/month) [^73].

Architecture:
    Twilio μ-law 8kHz ──► decode ──► 16kHz PCM ──► buffer ──► VAD
                                              │
                                              ▼
                                        Deepgram Nova-3 STT
                                              │
                                              ▼
                              Azure OpenAI GPT-4o-mini (tool calling)
                                              │
                                              ▼
                                        Deepgram Aura TTS
                                              │
                                              ▼
                                        24kHz PCM ──► resample ──► 8kHz ──► μ-law
                                                                                │
                                                                                ▼
                                                                        Twilio WebSocket

Refs:
    - [^61]: Deepgram. (2024). Nova-3 Model Documentation.
    - [^69]: OpenAI. (2024). GPT-4o-mini pricing.
    - [^70]: Deepgram. (2024). Aura TTS documentation.
    - [^73]: Microsoft. (2024). Azure pricing calculator.
"""

from __future__ import annotations

import os
import sys
import base64
import asyncio
import tempfile
import wave
from pathlib import Path
from typing import Optional, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.telephony.twilio_gateway import TwilioGateway
from src.telephony._audio_compat import ratecv, lin2ulaw
from src.receptionist.service import Receptionist, CallSession

from src.domains.registry import DomainRegistry
from src.domains.router import DomainRouter
from src.infrastructure.interfaces import DomainPort

from src.infrastructure.demo_pipeline import AudioBuffer
from src.infrastructure.azure_openai_client import AzureOpenAILLMClient
from src.infrastructure.deepgram_tts_client import DeepgramTTSClient
from src.infrastructure.demo_stt_deepgram import DemoSTTDeepgram
from src.emotion.tts_prosody import TTSProsodyMapper


# ---------------------------------------------------------------------------
# Production Pipeline Orchestrator
# ---------------------------------------------------------------------------

class ProductionPipeline:
    """
    Cloud-only pipeline: Deepgram STT → Azure OpenAI LLM → Deepgram Aura TTS.
    No local models. Designed for ACA deployment.
    """

    def __init__(
        self,
        domain_registry: DomainRegistry,
        domain_router: DomainRouter,
        default_domain: str = "construction",
    ):
        self.gateway = TwilioGateway()
        self.stt = DemoSTTDeepgram(language="en-IN")
        self.tts = DeepgramTTSClient()
        self.prosody_mapper = TTSProsodyMapper()  # [^E12][^E14]: emotion-to-voice mapping
        self.domain_registry = domain_registry
        self.domain_router = domain_router
        self.default_domain = default_domain
        self._receptionists: Dict[str, Receptionist] = {}
        self._session_receptionist: Dict[str, Receptionist] = {}
        self._buffers: Dict[str, AudioBuffer] = {}
        self._processing: set = set()

    def _get_or_create_receptionist(self, domain_id: str) -> Receptionist:
        if domain_id in self._receptionists:
            return self._receptionists[domain_id]

        domain = self.domain_registry.get(domain_id)
        if domain is None:
            raise ValueError(f"Unknown domain: {domain_id}")

        llm = AzureOpenAILLMClient()
        receptionist = domain.create_receptionist(llm_client=llm, tts_provider=None)
        self._receptionists[domain_id] = receptionist
        return receptionist

    async def on_call_start(
        self,
        session_id: str,
        caller: str,
        called: str,
        domain_id: Optional[str] = None,
    ) -> bytes:
        """
        Initialize a call session.

        Args:
            session_id: Unique call/session identifier.
            caller: Caller phone number (from).
            called: Called phone number (to).
            domain_id: Optional explicit domain override (e.g., from TwiML
                custom parameters for outbound calls). If provided, skips
                phone-number-based routing [^43].
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

        greeting_text = await receptionist.handle_call_start(session_id, caller, called)
        self._buffers[session_id] = AudioBuffer()
        return self._synthesize_to_ulaw(greeting_text, emotion_tone=None)

    async def on_media_chunk(self, session_id: str, payload_b64: str) -> Optional[bytes]:
        mulaw_bytes = base64.b64decode(payload_b64)
        pcm_16k = self.gateway.decode_inbound(mulaw_bytes)

        buf = self._buffers.get(session_id)
        if buf is None:
            return None

        is_speech_end = buf.ingest(pcm_16k)
        if not is_speech_end:
            return None

        if session_id in self._processing:
            return None
        self._processing.add(session_id)

        try:
            response_audio = await self._process_utterance(session_id, buf)
            return response_audio
        finally:
            self._processing.discard(session_id)
            buf.reset()

    async def on_call_end(self, session_id: str) -> Optional[CallSession]:
        self._buffers.pop(session_id, None)
        receptionist = self._session_receptionist.pop(session_id, None)
        if receptionist is None:
            return None
        try:
            return await receptionist.handle_call_end(session_id)
        except ValueError:
            return None

    async def _process_utterance(self, session_id: str, buf: AudioBuffer) -> Optional[bytes]:
        loop = asyncio.get_event_loop()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        buf.to_wav(tmp_path)

        try:
            transcript = await loop.run_in_executor(None, self.stt.transcribe, tmp_path)

            if not transcript or len(transcript.strip()) < 3:
                print(f"[{session_id}] STT: <noise/empty>")
                return None

            print(f"[{session_id}] STT: {transcript}")

            receptionist = self._session_receptionist.get(session_id)
            if receptionist is None:
                return None

            response_text = await receptionist.handle_transcript(session_id, transcript)
            print(f"[{session_id}] LLM: {response_text}")

            # Extract latest emotion tone for TTS prosody mapping [^E12][^E14]
            from src.emotion.profile import EmotionalTone
            emotion_tone = None
            rec = receptionist
            machine = rec._emotion_machines.get(session_id) if hasattr(rec, '_emotion_machines') else None
            if machine and machine.latest_target_tone:
                emotion_tone = machine.latest_target_tone
                # Check escalation — offer human handoff if needed [^E9]
                if machine.should_offer_human:
                    response_text += " Would you like me to connect you with a human representative?"

            response_audio = await loop.run_in_executor(
                None, self._synthesize_to_ulaw, response_text, emotion_tone
            )
            return response_audio
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _synthesize_to_ulaw(self, text: str, emotion_tone=None) -> bytes:
        """
        Synthesize text with emotion-mapped prosody and voice selection.
        [^E12]: Deepgram Aura voice selected by emotion.
        [^E14]: Text prosody cues injected by TTSProsodyMapper.
        """
        from src.emotion.profile import EmotionalTone
        target = emotion_tone or EmotionalTone.CALM
        adapted_text, voice_model = self.prosody_mapper.map(text, target)
        pcm_24k = self.tts.synthesize(adapted_text, model=voice_model)
        # Deepgram Aura returns WAV with header. Parse to get raw PCM.
        import io
        wav_buffer = io.BytesIO(pcm_24k)
        with wave.open(wav_buffer, "rb") as w:
            pcm_24k_raw = w.readframes(w.getnframes())
        # Resample 24kHz → 8kHz
        pcm_8k, _ = ratecv(pcm_24k_raw, 2, 1, 24000, 8000, None)
        # Encode to μ-law
        mulaw = lin2ulaw(pcm_8k, 2)
        return mulaw
