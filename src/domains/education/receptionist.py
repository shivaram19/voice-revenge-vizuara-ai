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
    # Override: _build_messages — inject scenario posture + parent record.
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

        if self._tenant is not None:
            # Tenant renders scenario posture + record block as a single
            # overlay; the prompt template inlines it as `parent_block`.
            merged_context["parent_block"] = self._tenant.render_prompt_overlay(
                record, scenario
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
        return await super().handle_call_end(session_id)


# References
# - "Parent data contract" project memory (2026-04-30).
# - ADR-009 / ADR-013, DFS-007.
# [^95]: Gamma et al. 1994 (Template Method).
