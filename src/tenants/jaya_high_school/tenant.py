"""
Jaya High School — Tenant Facade
==================================
Single object that the runtime asks for everything tenant-specific:
school identity, parent records, scenario templates. Composed from the
sibling modules `config.py`, `parents.py`, and `scenarios/`.

Future production: an analogous Tenant class for each new school
(``tenants/zilla_parishad_high.py``, ``tenants/sri_chaitanya.py``, …)
sharing this same shape; runtime resolution by ``ACTIVE_TENANT_ID``
or by Twilio caller-ID mapping.

Ref: ADR-009 (domain modularity); user dialogue 2026-04-30
     ("build separate module jayahigh school system").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.domains.education.parent_registry import ParentRecord
from src.tenants.jaya_high_school.config import JAYA_SCHOOL_CONFIG, SchoolConfig
from src.tenants.jaya_high_school.parents import JAYA_PARENT_RECORDS
from src.tenants.jaya_high_school.scenarios import (
    Scenario,
    SCENARIOS,
    pick_scenario,
)


@dataclass(frozen=True)
class Tenant:
    """A single tenant (school) — identity + data + conversational templates."""

    tenant_id: str
    config: SchoolConfig
    parent_records: List[ParentRecord]
    scenarios: Dict[str, Scenario]

    def lookup_parent(self, phone: str) -> Optional[ParentRecord]:
        """Phone-keyed lookup, tolerant to formatting (delegates to registry)."""
        from src.domains.education.parent_registry import ParentRegistry

        return ParentRegistry(self.parent_records).lookup(phone)

    def scenario_for(self, record: Optional[ParentRecord]) -> Optional[Scenario]:
        """
        Default-by-status scenario resolution. A future revision will let
        a record carry an explicit `next_call_scenario` override (e.g. an
        attendance_followup call to a parent whose fees are paid).
        """
        return pick_scenario(record)

    def scenario_by_id(self, scenario_id: str) -> Optional[Scenario]:
        return self.scenarios.get(scenario_id)

    def render_prompt_overlay(
        self,
        record: Optional[ParentRecord],
        scenario: Optional[Scenario],
        pivot_hint: str = "",
        news_offer_hint: str = "",
        news_block: str = "",
        intent_shift_hint: str = "",
    ) -> str:
        """
        Compose the scenario posture_note + parent record block + any
        turn-scoped post-intent hints (pivot OR news offer) into a
        single overlay for the LLM system prompt.

        At most ONE of pivot_hint / news_offer_hint should be non-empty
        for any given turn; the receptionist sequences them across
        consecutive turns so the parent never gets two questions at once.

        Args:
            record: verified ParentRecord, or None if not loaded.
            scenario: the active Scenario for this call.
            pivot_hint: text of the post-intent pivot to offer this turn.
            news_offer_hint: text of the news-offer question this turn.
            news_block: rendered upcoming-events block (only included
                with news_offer_hint, so the LLM has source material if
                the parent accepts).
        """
        chunks: List[str] = []
        if scenario is not None:
            chunks.append(scenario.posture_note.rstrip())
        if record is not None:
            chunks.append(record.to_prompt_block())
            # Inject the rendered opening + closing templates as
            # near-verbatim guidance. The LLM was observed (call
            # CA30cc18..., 2026-04-30) to ignore the Telangana
            # code-mix templates and revert to plain English with a
            # single Telugu loanword. Surfacing the actual template
            # in the prompt with explicit "speak this verbatim"
            # framing nudges the model to honour the regional register.
            if scenario is not None:
                summary = scenario.render_intent_summary(record)
                details = scenario.render_intent_details(record)
                closing = scenario.render_closing(record)
                chunks.append(
                    "## TURN 3 — SPEAK VERBATIM AFTER THE PARENT'S "
                    "\"Cheppandi\" / \"Yes\" / \"Hello\"\n"
                    "(Telangana-register intent SUMMARY; pause and let "
                    "the parent acknowledge before continuing — do NOT "
                    "deliver the details in this same turn):\n\n"
                    f"\"{summary}\""
                )
                if details:
                    chunks.append(
                        "## TURN 5 — SPEAK VERBATIM AFTER THE PARENT'S "
                        "ACKNOWLEDGMENT (\"Avuna\" / \"Sare\" / \"OK\" / "
                        "\"Yes\" / silence-then-listening)\n"
                        "(Telangana-register intent DETAILS; verified "
                        "data + thanks; do NOT paraphrase into plain "
                        "English):\n\n"
                        f"\"{details}\""
                    )
                chunks.append(
                    "## SUGGESTED CLOSING — speak when intent has been "
                    "delivered AND the parent signals wrap-up. After "
                    "this line, the call ends; do not extend further.\n"
                    f"\"{closing}\""
                )
        else:
            chunks.append(
                "## VERIFIED PARENT RECORD\n"
                "(no record loaded for this call — admit honestly if asked)"
            )
        if intent_shift_hint:
            chunks.append(
                "## TURN-SCOPED HINT (apply ONLY to this immediate reply)\n"
                + intent_shift_hint
            )
        if pivot_hint:
            chunks.append(
                "## TURN-SCOPED HINT (apply ONLY to this immediate reply)\n"
                "The primary call objective is satisfied — the parent has "
                "signalled wrap-up. In your reply, gently offer this "
                "pivot once, in your own natural words, before any final "
                "closing:\n"
                f"\"{pivot_hint}\"\n"
                "Keep it ≤15 words. If the parent declines or sounds "
                "rushed, accept gracefully and close warmly. Do not "
                "repeat the pivot in any later turn."
            )
        elif news_offer_hint:
            chunks.append(
                "## TURN-SCOPED HINT (apply ONLY to this immediate reply)\n"
                "The primary call objective is satisfied. Offer this "
                "broader news question once, in your own natural words:\n"
                f"\"{news_offer_hint}\"\n"
                "Keep the question ≤14 words. If the parent says yes, "
                "share at most TWO upcoming events from the news block "
                "below in subsequent turns. If they decline, close warmly."
            )
            if news_block:
                chunks.append(news_block)
        return "\n\n".join(chunks)


JAYA_HIGH_SCHOOL = Tenant(
    tenant_id="jaya-suryapet",
    config=JAYA_SCHOOL_CONFIG,
    parent_records=JAYA_PARENT_RECORDS,
    scenarios=SCENARIOS,
)


__all__ = ["Tenant", "JAYA_HIGH_SCHOOL"]
