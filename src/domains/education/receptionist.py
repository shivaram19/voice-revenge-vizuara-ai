"""
Education Receptionist — Personalized via Verified Parent Records
==================================================================
Subclass of BaseReceptionist that, at call start, looks up the parent
record by phone number and:
  1. Renders a personalized, status-aware greeting.
  2. Injects the verified record into the system prompt so the LLM
     speaks supportively from authoritative data instead of probing
     for information.

Ref: Gamma et al. 1994 (Template Method) [^95];
     "Parent data contract" project memory (2026-04-30);
     ADR-013 (patience), DFS-007 (Suryapet demographic).
"""

from typing import Any, Dict, List, Optional

from src.receptionist.base_receptionist import BaseReceptionist
from src.receptionist.service import CallSession, ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry
from src.domains.education.prompts import build_education_prompt
from src.domains.education.parent_registry import ParentRecord, ParentRegistry


class EducationReceptionist(BaseReceptionist):
    """
    Concrete receptionist for the education domain.
    Personalizes every call with a verified parent record when available.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._registry = ParentRegistry()
        self._parent_records: Dict[str, Optional[ParentRecord]] = {}

    # ------------------------------------------------------------------
    # Override: handle_call_start so we can resolve the parent record
    # *before* the greeting is generated and personalize the greeting.
    # ------------------------------------------------------------------

    async def handle_call_start(
        self, session_id: str, caller: str, called: str
    ) -> str:
        from src.emotion.profile import EmotionWindow
        from src.emotion.state_machine import EmotionStateMachine

        # Look up parent — try `called` (outbound) then `caller` (inbound).
        record = self._registry.lookup(called) or self._registry.lookup(caller)
        self._parent_records[session_id] = record

        session = CallSession(
            session_id=session_id,
            caller_number=caller,
            called_number=called,
            emotion_window=EmotionWindow(),
        )
        self.sessions[session_id] = session
        self._emotion_machines[session_id] = EmotionStateMachine()

        greeting = self._greeting_for(record)
        session.conversation_history.append(
            {"role": "assistant", "content": greeting}
        )
        return greeting

    # Required by ABC — used only when no record is loaded for the session
    # (e.g., a future inbound call before lookup resolves).
    def _greeting_text(self) -> str:
        return self._greeting_for(None)

    def _greeting_for(self, record: Optional[ParentRecord]) -> str:
        """
        Status-aware, short, outbound greeting.
        Per ADR-013: ≤18 words, single question, no marketing language.
        """
        company = self.config.company_name
        if record is None:
            return (
                f"Namaste sir. This is calling from {company}. "
                "I have a small reminder about your child's school fees. "
                "Is this a good time to speak?"
            )

        addr = f"{record.salutation} {record.parent_name}"
        if record.status == "PAID_IN_FULL":
            return (
                f"Namaste {addr}. This is calling from {company} "
                f"about {record.child_name}'s school fees. "
                "Is this a good time to speak, sir?"
            )
        if record.status == "PARTIAL":
            return (
                f"Namaste {addr}. This is calling from {company} "
                f"about {record.child_name}'s fees for this term. "
                "Is this a good time to speak, sir?"
            )
        # UNPAID
        return (
            f"Namaste {addr}. This is calling from {company} "
            f"regarding {record.child_name}'s school fees. "
            "Is this a good time to speak, sir?"
        )

    # ------------------------------------------------------------------
    # Override: _build_messages to inject the verified-record block
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        session: CallSession,
        today_date: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        record = self._parent_records.get(session.session_id)
        merged_context: Dict[str, Any] = dict(context or {})
        if record is not None:
            merged_context["parent_block"] = record.to_prompt_block()
        return build_education_prompt(
            company_name=self.config.company_name,
            hours_text=self.config.hours_text,
            today_date=today_date,
            conversation_history=session.conversation_history,
            context=merged_context,
        )

    # ------------------------------------------------------------------
    # Override: handle_call_end to clean up parent-record cache
    # ------------------------------------------------------------------

    async def handle_call_end(self, session_id: str) -> CallSession:
        self._parent_records.pop(session_id, None)
        return await super().handle_call_end(session_id)


# References
# - "Parent data contract" project memory (2026-04-30).
# - ADR-009 / ADR-013, DFS-007.
# [^95]: Gamma et al. 1994 (Template Method).
