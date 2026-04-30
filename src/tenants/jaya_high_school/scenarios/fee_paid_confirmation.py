"""
Scenario: Fee Paid In Full — Supportive Confirmation
=====================================================
Most common production flow. The parent has already paid for the
current term. Job: confirm warmly, thank, and close. Do NOT ask for
money. Do NOT pitch new courses. Aim for ≤4 turns end-to-end.
"""

from __future__ import annotations

from src.domains.education.parent_registry import ParentRecord
from src.tenants.jaya_high_school.scenarios.base import Scenario


def _opening(record: ParentRecord) -> str:
    last = record.payments[-1] if record.payments else None
    paid_str = f"₹{record.term_fee_total_inr:,}"
    on_date = f" on {last.date}" if last else ""
    return (
        f"Thank you for taking the call, sir. "
        f"I am calling to confirm that {record.child_name}'s fee of "
        f"{paid_str} for {record.term_label} has been received{on_date}. "
        "Everything is settled."
    )


def _closing(record: ParentRecord) -> str:
    return (
        f"Thank you for your prompt payment, sir. "
        f"Have a peaceful day."
    )


def _pivot(record: ParentRecord) -> str:
    """
    Once the parent has acknowledged the fee confirmation and is winding
    down, gently offer a related topic — admission referral. Phrased as
    a single, easy-to-decline question. Never offered if the parent
    sounds rushed or distressed.
    """
    return (
        f"Sir, before I let you go — "
        f"do you know any family considering admission for next year? "
        f"We would be happy to share details with them, "
        f"or you may pass our office number along."
    )


SCENARIO = Scenario(
    scenario_id="fee_paid_confirmation",
    objective=(
        "Confirm that the parent's term fees are settled, thank them, "
        "and close warmly. No new asks."
    ),
    opening_line=_opening,
    closing_line=_closing,
    posture_note=(
        "## Scenario: SUPPORTIVE CONFIRMATION (fees paid in full)\n"
        "- The parent has paid in full. The call is purely a courtesy.\n"
        "- Lead with gratitude. Acknowledge the child by name once.\n"
        "- Do NOT ask for any payment. Do NOT pitch new courses, batches, "
        "or upcoming fees on this call — it would feel like a bait-and-switch.\n"
        "- If the parent asks an unrelated question (transport, exams, school "
        "event), answer briefly from FAQ knowledge if available, otherwise "
        "say the office will follow up.\n"
        "- Aim to close within 3-4 turns once the parent confirms they "
        "heard you. Don't keep them on the line out of politeness."
    ),
    success_signals=(
        "thank you",
        "thanks",
        "okay sir",
        "alright",
        "noted",
        "bye",
        "goodbye",
        "thank you very much",
    ),
    post_intent_pivot=_pivot,
)
