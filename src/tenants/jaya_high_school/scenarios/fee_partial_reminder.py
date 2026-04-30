"""
Scenario: Partial Payment — Gentle Balance Reminder
=====================================================
Parent has paid some, owes the rest. Job: thank them for the partial
payment, mention the outstanding balance once, ask if they have
questions or need an installment plan, never pressure.
"""

from __future__ import annotations

from src.domains.education.parent_registry import ParentRecord
from src.tenants.jaya_high_school.honorifics import thanks, vocative
from src.tenants.jaya_high_school.scenarios.base import Scenario


def _opening(record: ParentRecord) -> str:
    paid = f"₹{record.fee_paid_total_inr:,}"
    balance = f"₹{record.fee_balance_inr:,}"
    return (
        f"{thanks(record)} for taking the call, {vocative(record)}. "
        f"I see you have paid {paid} of {record.child_name}'s fees. "
        f"A balance of {balance} remains for {record.term_label}, "
        f"due by {record.fee_due_date}."
    )


def _closing(record: ParentRecord) -> str:
    voc = vocative(record)
    return (
        f"{thanks(record)}, {voc}. The office will note this conversation. "
        f"Have a peaceful day, {voc}."
    )


def _news_offer(record: ParentRecord) -> str:
    """
    For partial-payment parents, after the conversation about the
    balance has wound down respectfully, offer a brief broader
    follow-up about upcoming events. Strictly OFF-RAMP — do NOT
    offer this if the parent sounded stressed about money.
    """
    return (
        f"Sir, would you also like to know about anything happening "
        f"at school in the coming weeks?"
    )


SCENARIO = Scenario(
    scenario_id="fee_partial_reminder",
    objective=(
        "Acknowledge the partial payment with thanks, mention the "
        "balance and due date once, offer installment if asked. Close warmly."
    ),
    opening_line=_opening,
    closing_line=_closing,
    posture_note=(
        "## Scenario: GENTLE BALANCE REMINDER (partial payment received)\n"
        "- Begin by thanking them for the partial payment they have made.\n"
        "- Mention the balance ONCE — do not repeat figures across turns.\n"
        "- Offer installment options only if the parent expresses concern "
        "or asks: 'a 3-month EMI is available without extra cost'.\n"
        "- If they commit to a date or method, acknowledge: 'Noted sir, "
        "I will inform the office.' Do not record promises beyond what "
        "they explicitly said.\n"
        "- Never threaten consequences. Never imply the child will be "
        "withdrawn or excluded from anything.\n"
        "- If they say they cannot pay right now, respond with empathy: "
        "'I understand sir. May the office call you back at a better time?'"
    ),
    post_intent_news_offer=_news_offer,
)
