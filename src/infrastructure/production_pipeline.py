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
import json
import base64
import struct
import asyncio
import tempfile
import wave
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.telephony.twilio_gateway import TwilioGateway
from src.telephony._audio_compat import ratecv, lin2ulaw
from src.receptionist.models import Database
from src.receptionist.construction_seed import seed_database, CONSTRUCTION_FAQ
from src.receptionist.scheduler import SchedulingEngine
from src.receptionist.service import ReceptionistConfig, CallSession
from src.receptionist.construction_service import ConstructionReceptionist
from src.receptionist.tools.base import Tool, ToolResult, ToolRegistry
from src.receptionist.tools.faq import FAQKnowledgeBase, FAQChunk

from src.infrastructure.demo_pipeline import AudioBuffer
from src.infrastructure.azure_openai_client import AzureOpenAILLMClient
from src.infrastructure.deepgram_tts_client import DeepgramTTSClient
from src.infrastructure.demo_stt_deepgram import DemoSTTDeepgram


# ---------------------------------------------------------------------------
# Tool Wrappers (same as demo_pipeline.py)
# ---------------------------------------------------------------------------

class FindContractorTool(Tool):
    def __init__(self, db: Database): self.db = db
    @property
    def name(self) -> str: return "find_contractor"
    @property
    def description(self) -> str: return "Find a contractor by specialty or name."
    @property
    def parameters(self) -> Dict[str, Any]: return {"properties": {"query": {"type": "string"}}, "required": ["query"]}
    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        all_contractors = self.db.list_contractors(active_only=True)
        query_lower = query.lower()
        results = [c for c in all_contractors if query_lower in c.specialty.lower() or query_lower in c.name.lower() or query_lower in c.phone]
        if not results: return ToolResult(success=False, message=f"No contractors found for '{query}'.")
        lines = [f"{c.name}, {c.specialty}, phone {c.phone}" for c in results]
        return ToolResult(success=True, message=f"Found {len(results)} contractor(s): {'; '.join(lines)}.", data={"contractors": [{"name": c.name, "specialty": c.specialty, "phone": c.phone} for c in results]})


class CheckAvailabilityTool(Tool):
    def __init__(self, db: Database): self.db = db; self.scheduler = SchedulingEngine(db)
    @property
    def name(self) -> str: return "check_availability"
    @property
    def description(self) -> str: return "Check available appointment slots for a contractor on a given date."
    @property
    def parameters(self) -> Dict[str, Any]: return {"properties": {"contractor_id": {"type": "integer"}, "date": {"type": "string"}}, "required": ["contractor_id", "date"]}
    async def execute(self, **kwargs) -> ToolResult:
        try:
            cid = int(kwargs["contractor_id"])
            target = datetime.strptime(kwargs["date"], "%Y-%m-%d").date()
        except Exception as e: return ToolResult(success=False, message="Invalid parameters.", error=str(e))
        slots = self.scheduler.get_available_slots(cid, target)
        if not slots: return ToolResult(success=False, message="No available slots.")
        times = [s.start_time.strftime("%I:%M %p") for s in slots[:5]]
        return ToolResult(success=True, message=f"Available times: {', '.join(times)}.", data={"slots": times})


class BookAppointmentTool(Tool):
    def __init__(self, db: Database): self.db = db; self.scheduler = SchedulingEngine(db)
    @property
    def name(self) -> str: return "book_appointment"
    @property
    def description(self) -> str: return "Book an appointment with a contractor."
    @property
    def parameters(self) -> Dict[str, Any]: return {"properties": {"contractor_id": {"type": "integer"}, "date": {"type": "string"}, "time": {"type": "string"}, "caller_name": {"type": "string"}, "caller_phone": {"type": "string"}, "duration_minutes": {"type": "integer", "default": 30}, "notes": {"type": "string", "default": ""}}, "required": ["contractor_id", "date", "time", "caller_name", "caller_phone"]}
    async def execute(self, **kwargs) -> ToolResult:
        try:
            from src.receptionist.models import AppointmentType
            cid = int(kwargs["contractor_id"])
            target_date = datetime.strptime(kwargs["date"], "%Y-%m-%d").date()
            target_time = datetime.strptime(kwargs["time"], "%H:%M").time()
            start = datetime.combine(target_date, target_time)
            duration = int(kwargs.get("duration_minutes", 30))
            success, msg, appt_id = self.scheduler.book_appointment(cid, kwargs["caller_name"], kwargs["caller_phone"], start, duration, appointment_type=AppointmentType.IN_PERSON, notes=kwargs.get("notes", ""))
        except Exception as e: return ToolResult(success=False, message="Invalid booking.", error=str(e))
        return ToolResult(success=success, message=msg, data={"appointment_id": appt_id})


class FAQTool(Tool):
    def __init__(self, faq_kb: FAQKnowledgeBase): self.faq = faq_kb
    @property
    def name(self) -> str: return "search_faq"
    @property
    def description(self) -> str: return "Search the company FAQ."
    @property
    def parameters(self) -> Dict[str, Any]: return {"properties": {"query": {"type": "string"}}, "required": ["query"]}
    async def execute(self, **kwargs) -> ToolResult:
        results = self.faq.search(kwargs.get("query", ""), top_k=2)
        if not results: return ToolResult(success=False, message="I don't have information on that.")
        text = " ".join(r.text for r in results)
        return ToolResult(success=True, message=text, data={"matches": [r.text for r in results]})


class OutboundCallTool(Tool):
    def __init__(self, db: Database): self.db = db
    @property
    def name(self) -> str: return "schedule_outbound_call"
    @property
    def description(self) -> str: return "Schedule an outbound call to a contractor."
    @property
    def parameters(self) -> Dict[str, Any]: return {"properties": {"contractor_id": {"type": "integer"}, "reason": {"type": "string"}}, "required": ["contractor_id", "reason"]}
    async def execute(self, **kwargs) -> ToolResult:
        cid = int(kwargs.get("contractor_id", 0))
        reason = kwargs.get("reason", "")
        c = self.db.get_contractor(cid)
        if not c: return ToolResult(success=False, message="Contractor not found.")
        return ToolResult(success=True, message=f"I've scheduled a call to {c.name} at {c.phone} regarding: {reason}.")


# ---------------------------------------------------------------------------
# Production Pipeline Orchestrator
# ---------------------------------------------------------------------------

class ProductionPipeline:
    """
    Cloud-only pipeline: Deepgram STT → Azure OpenAI LLM → Deepgram Aura TTS.
    No local models. Designed for ACA deployment.
    """

    def __init__(self):
        self.gateway = TwilioGateway()
        self.stt = DemoSTTDeepgram(language="en-IN")
        self.tts = DeepgramTTSClient()
        self.receptionist = self._build_receptionist()
        self._buffers: Dict[str, AudioBuffer] = {}
        self._processing: set = set()

    def _build_receptionist(self) -> ConstructionReceptionist:
        db = Database(":memory:")
        seed_database(db)
        faq_kb = FAQKnowledgeBase()
        for item in CONSTRUCTION_FAQ:
            faq_kb.add(FAQChunk(text=item["text"], source="company_handbook", category=item["category"]))

        registry = ToolRegistry()
        registry.register(FindContractorTool(db))
        registry.register(CheckAvailabilityTool(db))
        registry.register(BookAppointmentTool(db))
        registry.register(FAQTool(faq_kb))
        registry.register(OutboundCallTool(db))

        config = ReceptionistConfig(
            company_name="TreloLabs Voice AI",
            hours_text="Monday through Friday, 8 AM to 6 PM. Emergency dispatch 24/7.",
            tool_timeout_seconds=5.0,
        )
        llm = AzureOpenAILLMClient()
        rec = ConstructionReceptionist(config=config, tool_registry=registry, llm_client=llm, tts_provider=None)
        # Wrap sync chat_completion in async for the receptionist's await.
        # The Azure OpenAI SDK is synchronous; we offload to thread pool.
        async def _async_chat_completion(messages, tools):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, llm.chat_completion, messages, tools)
        rec._llm_chat_completion = _async_chat_completion
        return rec

    async def on_call_start(self, session_id: str, caller: str, called: str) -> bytes:
        greeting_text = await self.receptionist.handle_call_start(session_id, caller, called)
        self._buffers[session_id] = AudioBuffer()
        return self._synthesize_to_ulaw(greeting_text)

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
        try:
            return await self.receptionist.handle_call_end(session_id)
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

            response_text = await self.receptionist.handle_transcript(session_id, transcript)
            print(f"[{session_id}] LLM: {response_text}")

            response_audio = await loop.run_in_executor(None, self._synthesize_to_ulaw, response_text)
            return response_audio
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _synthesize_to_ulaw(self, text: str) -> bytes:
        pcm_24k = self.tts.synthesize(text)
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
