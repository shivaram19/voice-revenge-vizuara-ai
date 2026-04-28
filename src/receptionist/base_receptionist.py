"""
Base Receptionist — Template Method Pattern
============================================
Eliminates ~540 lines of duplication across 4 domain receptionists.
Subclasses override only:
  - _greeting_text()      → domain-specific greeting
  - _build_messages()     → domain-specific prompt builder

Ref: Gamma et al. 1994 (Template Method) [^95];
     Fowler 2018 (Remove Duplication) [^F1];
     Martin 2002 (DRY / SRP) [^94].
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.receptionist.service import Receptionist, CallSession, ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry
from src.streaming.sentence_aggregator import SentenceAggregator
from src.emotion.detector import EmotionDetector
from src.emotion.state_machine import EmotionStateMachine
from src.emotion.prompt_adapter import EmotionPromptAdapter


@dataclass
class LLMResponse:
    """Normalised LLM response, provider-agnostic."""
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    is_tool_call: bool = False


class BaseReceptionist(Receptionist, ABC):
    """
    Template-method base for all domain receptionists.

    Shared responsibilities (this class):
        - Session lifecycle management
        - Emotion detection & prompt adaptation
        - ReAct loop orchestration (LLM Phase 1 → tool → LLM Phase 2)
        - LLM timeout handling & response normalisation
        - Thread-pool delegation for sync LLM clients

    Subclass responsibilities (~15 lines each):
        - _greeting_text()      → domain-specific opening
        - _build_messages()     → domain-specific system prompt + context
    """

    def __init__(
        self,
        config: ReceptionistConfig,
        tool_registry: ToolRegistry,
        llm_client: Any,
        tts_provider: Any,
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

    # ------------------------------------------------------------------
    # Template methods — subclasses override these
    # ------------------------------------------------------------------

    @abstractmethod
    def _greeting_text(self) -> str:
        """Return the domain-specific greeting message."""
        pass

    @abstractmethod
    def _build_messages(
        self,
        session: CallSession,
        today_date: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Build the messages list (system prompt + conversation history)
        for the current turn.
        """
        pass

    # ------------------------------------------------------------------
    # Receptionist ABC implementation
    # ------------------------------------------------------------------

    async def handle_call_start(self, session_id: str, caller: str, called: str) -> str:
        """Initialise session and return domain-specific greeting."""
        from src.emotion.profile import EmotionWindow
        session = CallSession(
            session_id=session_id,
            caller_number=caller,
            called_number=called,
            emotion_window=EmotionWindow(),
        )
        self.sessions[session_id] = session
        self._emotion_machines[session_id] = EmotionStateMachine()

        greeting = self._greeting_text()
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

        # Build context with domain-specific prompt
        today_date = datetime.utcnow().strftime("%A, %B %d, %Y")
        messages = self._build_messages(session, today_date, context={})

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

    def get_emotion_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Return emotion state for TTS prosody mapping.
        Fixes LSP violation: pipeline no longer uses hasattr introspection.
        """
        machine = self._emotion_machines.get(session_id)
        if machine is None:
            return None
        return {
            "latest_target_tone": machine.latest_target_tone,
            "should_offer_human": machine.should_offer_human,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
        """Delegate to injected LLM client via thread pool. DIP satisfied."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.llm.chat_completion, messages, tools)


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
# [^94]: Martin, R. C. (2002). Agile Software Development: Principles, Patterns, and Practices. Prentice Hall.
# [^95]: Gamma, E., et al. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
