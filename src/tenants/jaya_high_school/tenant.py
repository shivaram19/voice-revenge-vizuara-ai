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
    ) -> str:
        """
        Compose the scenario posture_note + parent record block + an
        optional turn-scoped pivot hint into a single overlay the LLM
        system prompt appends to its base instructions.

        ``pivot_hint`` is the post-intent pivot text. When non-empty,
        a "this turn only" instruction is appended telling the LLM to
        offer the pivot once and then close based on the parent's
        response. Caller is responsible for setting it only on the
        single turn where the pivot should fire.
        """
        chunks: List[str] = []
        if scenario is not None:
            chunks.append(scenario.posture_note.rstrip())
        if record is not None:
            chunks.append(record.to_prompt_block())
        else:
            chunks.append(
                "## VERIFIED PARENT RECORD\n"
                "(no record loaded for this call — admit honestly if asked)"
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
        return "\n\n".join(chunks)


JAYA_HIGH_SCHOOL = Tenant(
    tenant_id="jaya-suryapet",
    config=JAYA_SCHOOL_CONFIG,
    parent_records=JAYA_PARENT_RECORDS,
    scenarios=SCENARIOS,
)


__all__ = ["Tenant", "JAYA_HIGH_SCHOOL"]
