"""
Education Receptionist — Tenant- and Scenario-Aware
====================================================
Subclass of BaseReceptionist that, at call start, resolves the active
*tenant* (which school we're calling on behalf of), looks up the parent
record from that tenant's registry, picks the *scenario* the call falls
into (fee_paid_confirmation / fee_partial_reminder / fee_overdue_inquiry
/ admission_inquiry / attendance_followup), and renders a personalised
scenario-specific greeting plus a posture-and-record overlay for the LLM.

The generic education domain owns conversation orchestration; the tenant
module (`src/tenants/<tenant_id>/`) owns the school identity, parent data,
and scenario templates. This separation lets the same domain serve many
schools without duplicating prompt logic — only data and templates change.

Ref: Gamma et al. 1994 (Template Method) [^95];
     "Parent data contract" project memory (2026-04-30);
     ADR-013 (patience), DFS-007 (Suryapet demographic);
     user dialogue 2026-04-30 ("build separate module jayahigh school
     system", "templates that would be for different domains").
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
    Pulls tenant-specific data + scenario templates from the active
    Tenant facade (see `src.tenants.get_active_tenant`).
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Resolve the active tenant lazily so dev/test environments
        # without a tenant configured still work via the in-memory
        # ParentRegistry default seed.
        from src.tenants import get_active_tenant

        self._tenant = get_active_tenant()
        if self._tenant is not None:
            self._registry = ParentRegistry(self._tenant.parent_records)
        else:
            self._registry = ParentRegistry()

        self._parent_records: Dict[str, Optional[ParentRecord]] = {}
        self._scenarios: Dict[str, Optional[Any]] = {}
        # Post-intent pivot bookkeeping. `_intent_satisfied` flips True
        # the first time a caller utterance matches the active scenario's
        # success_signals. `_pivot_offered` flips True the first time we
        # inject the pivot hint into a prompt — preventing a second offer.
        self._intent_satisfied: Dict[str, bool] = {}
        self._pivot_offered: Dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Override: handle_call_start — resolve parent + scenario, then greet.
    # ------------------------------------------------------------------

    async def handle_call_start(
        self, session_id: str, caller: str, called: str
    ) -> str:
        from src.emotion.profile import EmotionWindow
        from src.emotion.state_machine import EmotionStateMachine

        # Look up parent — try `called` (outbound) then `caller` (inbound).
        record = self._registry.lookup(called) or self._registry.lookup(caller)
        self._parent_records[session_id] = record

        # Pick scenario via the tenant; fall back to status-only mapping
        # when no tenant is configured (dev mode).
        scenario = None
        if self._tenant is not None:
            scenario = self._tenant.scenario_for(record)
        self._scenarios[session_id] = scenario

        session = CallSession(
            session_id=session_id,
            caller_number=caller,
            called_number=called,
            emotion_window=EmotionWindow(),
        )
        self.sessions[session_id] = session
        self._emotion_machines[session_id] = EmotionStateMachine()

        # Reset pivot bookkeeping for this session.
        self._intent_satisfied[session_id] = False
        self._pivot_offered[session_id] = False

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
        Status-aware, short, outbound greeting. The greeting only
        identifies the school + child + topic and asks consent. The
        scenario-specific opening line (paid-in-full thanks, balance
        reminder, etc.) is delivered on the SECOND turn after the
        parent confirms it's a good time — keeps the greeting under
        ADR-013's 18-word budget.
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
    # Override: handle_transcript — detect intent satisfaction first,
    # then delegate to the base class for the LLM round-trip.
    # ------------------------------------------------------------------

    async def handle_transcript(
        self, session_id: str, transcript: str
    ) -> str:
        scenario = self._scenarios.get(session_id)
        if (
            scenario is not None
            and not self._intent_satisfied.get(session_id, False)
            and transcript
        ):
            text_lower = transcript.lower()
            if any(sig in text_lower for sig in scenario.success_signals):
                self._intent_satisfied[session_id] = True
        return await super().handle_transcript(session_id, transcript)

    # ------------------------------------------------------------------
    # Override: _build_messages — inject scenario posture + parent record,
    # and the post-intent pivot hint exactly once when due.
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        session: CallSession,
        today_date: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        record = self._parent_records.get(session.session_id)
        scenario = self._scenarios.get(session.session_id)
        merged_context: Dict[str, Any] = dict(context or {})

        # Decide whether THIS turn should carry the pivot hint.
        pivot_hint = ""
        if (
            scenario is not None
            and self._intent_satisfied.get(session.session_id, False)
            and not self._pivot_offered.get(session.session_id, False)
            and record is not None
        ):
            pivot_text = scenario.render_pivot(record)
            if pivot_text:
                pivot_hint = pivot_text
                # Mark before the LLM call so a future _build_messages on
                # the same turn (e.g. Phase 2 after a tool call) does not
                # re-inject. The flag is reset only on the next call.
                self._pivot_offered[session.session_id] = True

        if self._tenant is not None:
            merged_context["parent_block"] = self._tenant.render_prompt_overlay(
                record, scenario, pivot_hint=pivot_hint
            )
        elif record is not None:
            merged_context["parent_block"] = record.to_prompt_block()

        return build_education_prompt(
            company_name=self.config.company_name,
            hours_text=self.config.hours_text,
            today_date=today_date,
            conversation_history=session.conversation_history,
            context=merged_context,
        )

    # ------------------------------------------------------------------
    # Override: handle_call_end — purge per-session caches.
    # ------------------------------------------------------------------

    async def handle_call_end(self, session_id: str) -> CallSession:
        self._parent_records.pop(session_id, None)
        self._scenarios.pop(session_id, None)
        self._intent_satisfied.pop(session_id, None)
        self._pivot_offered.pop(session_id, None)
        return await super().handle_call_end(session_id)


# References
# - "Parent data contract" project memory (2026-04-30).
# - ADR-009 / ADR-013, DFS-007.
# [^95]: Gamma et al. 1994 (Template Method).
