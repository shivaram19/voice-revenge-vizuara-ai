"""
Scenario base type + resolver.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from src.domains.education.parent_registry import ParentRecord


@dataclass(frozen=True)
class Scenario:
    """
    A single conversational template: why we're calling, how we open,
    how we close, and the prompt overlay the LLM should use.

    Fields:
        scenario_id   — short snake_case identifier
        objective     — one-line statement of what the call is for
        opening_line  — agent's first utterance after the parent confirms
                        a good time to talk; receives the ParentRecord
                        for f-string-style substitution
        closing_line  — agent's natural close once the objective is met
        posture_note  — instructions injected into the LLM system prompt
                        describing how this scenario differs from others
                        (tone, what to volunteer, what to avoid)
        success_signals — phrases (lower-cased) the agent should treat as
                          conversation completion (e.g. "okay thank you")
    """

    scenario_id: str
    objective: str
    opening_line: Callable[[ParentRecord], str]
    closing_line: Callable[[ParentRecord], str]
    posture_note: str
    success_signals: tuple[str, ...] = (
        "thank you",
        "thanks",
        "okay sir",
        "noted",
        "bye",
        "goodbye",
    )

    def render_opening(self, record: ParentRecord) -> str:
        return self.opening_line(record)

    def render_closing(self, record: ParentRecord) -> str:
        return self.closing_line(record)


def pick_scenario(record: Optional[ParentRecord]) -> Optional[Scenario]:
    """
    Map a parent record to its default scenario based on fee status.

    Scenario chosen by status:
        PAID_IN_FULL → fee_paid_confirmation (supportive)
        PARTIAL      → fee_partial_reminder  (gentle)
        UNPAID       → fee_overdue_inquiry   (patient inquiry)

    Returns None if no record (caller should use a generic fallback).
    Future revisions will let the school explicitly tag a record with
    `next_call_scenario` to override the status-default mapping —
    e.g. for an admission_inquiry call to a parent whose fees are paid.
    """
    if record is None:
        return None
    # Local import — keeps the module-level import cycle clean.
    from src.tenants.jaya_high_school.scenarios import SCENARIOS

    if record.status == "PAID_IN_FULL":
        return SCENARIOS["fee_paid_confirmation"]
    if record.status == "PARTIAL":
        return SCENARIOS["fee_partial_reminder"]
    return SCENARIOS["fee_overdue_inquiry"]
