"""
Construction Receptionist — Concrete Implementation
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
from src.receptionist.prompts.construction_prompt import build_construction_prompt
from src.streaming.sentence_aggregator import SentenceAggregator


@dataclass
class LLMResponse:
    """Normalized LLM response, provider-agnostic."""
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    is_tool_call: bool = False


class ConstructionReceptionist(Receptionist):
    """
    Concrete receptionist for construction domain.
    Integrates: tool registry + LLM client + TTS provider.

    Architecture:
        Inbound audio → STT → LLM (with tools) → TTS → Outbound audio
        Tools: contractor lookup, scheduling, FAQ, outbound calling.
    """

    def __init__(
        self,
        config: ReceptionistConfig,
        tool_registry: ToolRegistry,
        llm_client,  # Any OpenAI-compatible client
        tts_provider,  # Any TTS provider
    ):
        self.config = config
        self.tools = tool_registry
        self.llm = llm_client
        self.tts = tts_provider
        self.sessions: Dict[str, CallSession] = {}
        self.aggregator = SentenceAggregator()

    async def handle_call_start(self, session_id: str, caller: str, called: str) -> str:
        """Initialize session and return construction-specific greeting."""
        session = CallSession(
            session_id=session_id,
            caller_number=caller,
            called_number=called,
        )
        self.sessions[session_id] = session

        greeting = (
            f"Thank you for calling {self.config.company_name}. "
            "I'm your virtual assistant. Are you calling for an emergency, "
            "to schedule an estimate, or something else?"
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

        # Build context with construction-specific prompt
        messages = build_construction_prompt(
            company_name=self.config.company_name,
            hours_text=self.config.hours_text,
            today_date=datetime.utcnow().strftime("%A, %B %d, %Y"),
            conversation_history=session.conversation_history,
        )

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

            # Phase 2: LLM synthesizes tool result into natural response
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
        """Finalize session and persist log."""
        session = self.sessions.pop(session_id, None)
        if not session:
            raise ValueError(f"Unknown session: {session_id}")
        session.state = "ended"
        return session

    def get_session(self, session_id: str) -> Optional[CallSession]:
        return self.sessions.get(session_id)

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        """Abstract LLM call. Production: Azure OpenAI client."""
        try:
            response = await asyncio.wait_for(
                self._llm_chat_completion(messages, tools),
                timeout=self.config.tool_timeout_seconds,
            )
        except asyncio.TimeoutError:
            # SigArch 2026: Timeout fillers mask >800ms latency [^16]
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
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
