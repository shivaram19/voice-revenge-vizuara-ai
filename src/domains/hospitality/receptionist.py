"""
Hospitality Receptionist — Concrete Implementation

OCP: Uses ToolRegistry so new tools are registered, not coded in.
DIP: Depends on Receptionist abstraction and Tool abstraction.
Ref: ReAct loop (Yao et al. 2023) [^74].
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.receptionist.service import Receptionist, CallSession, ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry, ToolResult
from src.domains.hospitality.prompts import build_hospitality_prompt
from src.emotion.detector import EmotionDetector
from src.emotion.state_machine import EmotionStateMachine
from src.emotion.prompt_adapter import EmotionPromptAdapter
from src.streaming.sentence_aggregator import SentenceAggregator


@dataclass
class LLMResponse:
    """Normalised LLM response, provider-agnostic."""
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    is_tool_call: bool = False


class HospitalityReceptionist(Receptionist):
    """
    Concrete receptionist for the hospitality domain.

    Integrates: tool registry + LLM client + TTS provider + emotion pipeline.

    Architecture:
        Inbound audio → STT → LLM (with tools) → TTS → Outbound audio
        Tools: room availability check, reservation booking, room service,
               concierge recommendations, FAQ search.
    """

    def __init__(
        self,
        config: ReceptionistConfig,
        tool_registry: ToolRegistry,
        llm_client,  # Any OpenAI-compatible client
        tts_provider,  # Any TTS provider
        emotion_detector: Optional[EmotionDetector] = None,
        prompt_adapter: Optional[EmotionPromptAdapter] = None,
    ):
        self.config = config
        self.tools = tool_registry
        self.llm = llm_client
        self.tts = tts_provider
        self.sessions: Dict[str, CallSession] = {}
        self.aggregator = SentenceAggregator()
        # Emotion pipeline — deterministic, auditable [^E4][^E5]
        self.emotion_detector = emotion_detector or EmotionDetector()
        self.prompt_adapter = prompt_adapter or EmotionPromptAdapter()
        self._emotion_machines: Dict[str, EmotionStateMachine] = {}

    async def handle_call_start(self, session_id: str, caller: str, called: str) -> str:
        """Initialise session and return hospitality-specific greeting."""
        from src.emotion.profile import EmotionWindow
        session = CallSession(
            session_id=session_id,
            caller_number=caller,
            called_number=called,
            emotion_window=EmotionWindow(),
        )
        self.sessions[session_id] = session
        self._emotion_machines[session_id] = EmotionStateMachine()

        greeting = (
            f"Thank you for calling {self.config.company_name}. "
            "I can help with room reservations, room service, or local recommendations. "
            "How may I assist you?"
        )
        session.conversation_history.append({"role": "assistant", "content": greeting})
        return greeting

    async def handle_transcript(self, session_id: str, transcript: str) -> str:
        """
        Process caller transcript through ReAct loop:
        observation → thought → action → observation.
        """
        session = self.sessions.get(session_id)
        if not session:
            return "Session error. Please call back."

        session.conversation_history.append({"role": "user", "content": transcript})

        # ---- Emotion pipeline [^E4][^E5] ----
        emotion_profile = self.emotion_detector.detect(transcript)
        emotion_machine = self._emotion_machines.get(session_id)
        if emotion_machine:
            emotion_machine.on_turn(emotion_profile)
        if session.emotion_window:
            session.emotion_window.append(emotion_profile)

        # Build context with hospitality-specific prompt
        messages = build_hospitality_prompt(
            company_name=self.config.company_name,
            hours_text=self.config.hours_text,
            today_date=datetime.utcnow().strftime("%A, %B %d, %Y"),
            conversation_history=session.conversation_history,
            context={},
        )

        # Inject emotion context into system prompt [^E4][^E8]
        if emotion_machine and messages:
            adapted_system = self.prompt_adapter.adapt_prompt(
                base_system_prompt=messages[0]["content"],
                detected_tone=emotion_machine.latest_tone,
                trajectory_name=emotion_machine.trajectory.name,
                consecutive_negative=emotion_machine.window.consecutive_negative_turns,
            )
            messages[0]["content"] = adapted_system

        # Get tool schemas from registry (OCP: tools added without code changes)
        tool_schemas = self.tools.schemas()

        # Phase 1: LLM decides tool or direct response
        llm_response = await self._call_llm(messages, tool_schemas)

        if llm_response.is_tool_call and llm_response.tool_name:
            # Execute tool via registry
            tool_result = await self.tools.execute(
                llm_response.tool_name,
                llm_response.tool_arguments or {},
            )

            # Phase 2: LLM synthesises tool result into natural response
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": f"call_{session_id}",
                    "type": "function",
                    "function": {
                        "name": llm_response.tool_name,
                        "arguments": json.dumps(llm_response.tool_arguments or {}),
                    },
                }],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": f"call_{session_id}",
                "content": tool_result.message,
            })

            final_response = await self._call_llm(messages, [])
            response_text = final_response.content or tool_result.message
        else:
            response_text = llm_response.content or "I'm not sure I understood. Could you rephrase that?"

        session.conversation_history.append({"role": "assistant", "content": response_text})
        return response_text

    async def handle_call_end(self, session_id: str) -> CallSession:
        """Finalise session and clean up state."""
        session = self.sessions.pop(session_id, None)
        self._emotion_machines.pop(session_id, None)
        if not session:
            raise ValueError(f"Unknown session: {session_id}")
        session.state = "ended"
        return session

    def get_session(self, session_id: str) -> Optional[CallSession]:
        """Retrieve an active session by ID."""
        return self.sessions.get(session_id)

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        """Abstract LLM call with timeout handling."""
        try:
            response = await asyncio.wait_for(
                self._llm_chat_completion(messages, tools),
                timeout=self.config.tool_timeout_seconds,
            )
        except asyncio.TimeoutError:
            # SigArch 2026: Timeout fillers mask >800 ms latency [^16]
            return LLMResponse(content="I'm still checking. One moment please.")

        if response.get("tool_calls"):
            tool_call = response["tool_calls"][0]
            return LLMResponse(
                is_tool_call=True,
                tool_name=tool_call["function"]["name"],
                tool_arguments=json.loads(tool_call["function"]["arguments"]),
            )

        return LLMResponse(content=response.get("content"))

    async def _llm_chat_completion(self, messages, tools):
        """Delegate to injected LLM client. DIP satisfied."""
        raise NotImplementedError("Connect to OpenAI-compatible LLM client")


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
