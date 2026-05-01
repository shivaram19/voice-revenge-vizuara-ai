"""
Receptionist Service Layer
Abstract base + legacy concrete implementation.
New code: use Receptionist (abstract) + ConstructionReceptionist (concrete).
Ref: Hexagonal Architecture (Cockburn 2005) [^42]; OpenAI (2023) [^13].
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from src.emotion.profile import EmotionWindow, EmotionState


# =============================================================================
# Abstract Base (DIP: domain depends on abstraction)
# =============================================================================

@dataclass
class CallSession:
    """Per-call state container. Ref: Newman 2015 [^28]."""
    session_id: str
    caller_number: str
    called_number: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    intent: Optional[str] = None
    contact_result: Optional[List] = None
    booking_result: Optional[Any] = None
    message_result: Optional[Any] = None
    misunderstanding_count: int = 0
    state: str = "idle"
    # Emotion state — added for controlled affective computing [^E4][^E5]
    emotion_window: Any = field(default_factory=lambda: None)  # EmotionWindow injected at runtime


@dataclass
class ReceptionistConfig:
    """Receptionist configuration. Ref: SigArch 2026 [^16]."""
    company_name: str = "TreloLabs Voice AI"
    hours_text: str = "Monday through Friday, 8 AM to 6 PM. Emergency dispatch 24/7."
    max_turns: int = 50
    tool_timeout_seconds: float = 3.0
    fallback_after_misunderstandings: int = 3


class Receptionist(ABC):
    """Abstract receptionist orchestrator."""

    @abstractmethod
    async def handle_call_start(self, session_id: str, caller: str, called: str) -> str:
        pass

    @abstractmethod
    async def handle_transcript(self, session_id: str, transcript: str) -> str:
        pass

    @abstractmethod
    async def handle_call_end(self, session_id: str) -> CallSession:
        pass

    @abstractmethod
    def get_emotion_state(self, session_id: str) -> Optional["EmotionState"]:
        """
        Return emotion state for TTS prosody mapping.
        Return None if emotion pipeline is not active.
        Fixes LSP: supertype defines contract instead of hasattr introspection.
        Ref: Meyer 1988 (Design by Contract) [^M1].
        """
        pass


# =============================================================================
# Legacy Concrete Implementation (backward compatible)
# =============================================================================

class ReceptionistService(Receptionist):
    """
    LEGACY: Generic receptionist for medical/corporate use.
    New construction projects: use ConstructionReceptionist instead.
    Kept for backward compatibility with existing demos.
    """

    def __init__(self, config, contacts, calendar, faq, messages, llm_client, tts_service):
        self.config = config
        self.contacts = contacts
        self.calendar = calendar
        self.faq = faq
        self.messages = messages
        self.llm = llm_client
        self.tts = tts_service
        self.sessions: Dict[str, CallSession] = {}

    async def handle_call_start(self, session_id: str, caller: str, called: str) -> str:
        session = CallSession(session_id=session_id, caller_number=caller, called_number=called)
        self.sessions[session_id] = session
        greeting = (
            f"Thank you for calling {self.config.company_name}. "
            "I'm the virtual receptionist. How can I help you today?"
        )
        session.conversation_history.append({"role": "assistant", "content": greeting})
        return greeting

    async def handle_transcript(self, session_id: str, transcript: str) -> str:
        session = self.sessions.get(session_id)
        if not session:
            return "Session error. Please call back."
        session.conversation_history.append({"role": "user", "content": transcript})

        from src.receptionist.prompts.system_prompt import build_prompt
        context = {}
        faq_chunks = self.faq.search(transcript)
        if faq_chunks:
            context["faq_chunks"] = [c.text for c in faq_chunks]

        messages = build_prompt(
            company_name=self.config.company_name,
            hours_text=self.config.hours_text,
            today_date=datetime.utcnow().strftime("%A, %B %d, %Y"),
            conversation_history=session.conversation_history,
            context=context,
        )

        tools = self._build_tool_definitions()
        response_text = await self._call_llm_with_tools(session, messages, tools)
        session.conversation_history.append({"role": "assistant", "content": response_text})
        return response_text

    async def handle_call_end(self, session_id: str) -> CallSession:
        session = self.sessions.pop(session_id, None)
        if not session:
            raise ValueError(f"Unknown session: {session_id}")
        session.state = "ended"
        return session

    def get_emotion_state(self, session_id: str) -> Optional[EmotionState]:
        """Legacy receptionist has no emotion pipeline."""
        return None

    def _build_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "lookup_contact",
                    "description": "Find an employee or department by name or role.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Name, role, or department to search for."},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_calendar",
                    "description": "Check availability or book an appointment. Confirm with the user before booking.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["check", "book"]},
                            "service": {"type": "string", "description": "Type of appointment."},
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                            "time": {"type": "string", "description": "Time in HH:MM format (24h). Required for booking."},
                            "name": {"type": "string", "description": "Caller name for booking."},
                        },
                        "required": ["action", "service", "date"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_faq",
                    "description": "Answer questions about the company using the knowledge base.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The user's question."},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "take_message",
                    "description": "Record a voicemail message for an employee. Confirm before saving.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {"type": "string", "description": "Who the message is for."},
                            "content": {"type": "string", "description": "The message content."},
                            "caller_name": {"type": "string"},
                            "urgent": {"type": "boolean", "default": False},
                        },
                        "required": ["recipient", "content", "caller_name"],
                    },
                },
            },
        ]

    async def _call_llm_with_tools(self, session, messages, tools):
        try:
            response = await asyncio.wait_for(
                self._llm_chat_completion(messages, tools),
                timeout=self.config.tool_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return "I'm still checking. One moment please."

        if response.get("tool_calls"):
            tool_call = response["tool_calls"][0]
            result = await self._execute_tool(session, tool_call)
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })
            final_response = await self._llm_chat_completion(messages, [])
            return final_response["content"]
        return response["content"]

    async def _llm_chat_completion(self, messages, tools):
        """Delegate to injected LLM client via thread pool. DIP satisfied."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.llm.chat_completion, messages, tools)

    async def _execute_tool(self, session, tool_call):
        name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])

        if name == "lookup_contact":
            results = self.contacts.lookup(args["query"])
            session.contact_result = results
            return self.contacts.format_for_voice(results)

        elif name == "check_calendar":
            from datetime import datetime as dt
            date_obj = dt.strptime(args["date"], "%Y-%m-%d")
            if args["action"] == "check":
                slots = self.calendar.check_availability(args["service"], date_obj)
                return self.calendar.format_slots_for_voice(slots)
            elif args["action"] == "book":
                time_obj = dt.strptime(args["time"], "%H:%M")
                start = date_obj.replace(hour=time_obj.hour, minute=time_obj.minute)
                result = self.calendar.book(
                    service=args["service"],
                    start=start,
                    duration_minutes=30,
                    booked_by=args["name"],
                )
                session.booking_result = result
                return result.message

        elif name == "search_faq":
            chunks = self.faq.search(args["query"])
            return self.faq.format_for_voice(chunks)

        elif name == "take_message":
            msg = self.messages.record(
                caller_name=args["caller_name"],
                caller_number=session.caller_number,
                recipient=args["recipient"],
                content=args["content"],
                urgent=args.get("urgent", False),
            )
            session.message_result = msg
            return self.messages.format_confirmation_for_voice(msg)

        return "Tool execution failed."


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
# [^28]: Newman, S. (2015). Building Microservices. O'Reilly.
# [^42]: Cockburn, A. (2005). Hexagonal Architecture.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
