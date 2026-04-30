"""
Scenario: Fee Unpaid / Overdue — Patient Inquiry
==================================================
Parent has not yet paid for the term. Job: ask if they received the
prior reminder, whether there are questions about the fee schedule
or payment options, never pressure. Many delays are practical (waiting
on a salary date, a sibling's payment, a family event); the agent's
role is to remove ambiguity, not to apply pressure.
"""

from __future__ import annotations

from src.domains.education.parent_registry import ParentRecord
from src.tenants.jaya_high_school.honorifics import thanks, vocative
from src.tenants.jaya_high_school.scenarios.base import Scenario


def _opening(record: ParentRecord) -> str:
    """Lead with intent (turn 3 of the cheppandi-pattern flow)."""
    is_telugu = (record.language_preference or "").strip().lower() == "telugu"
    total = f"₹{record.term_fee_total_inr:,}"

    if is_telugu:
        return (
            f"{record.child_name} school fees gurinchi call chesthunna, Garu. "
            f"{record.term_label} ki {total} due undi, "
            f"{record.fee_due_date} ki. Em question undha, Garu?"
        )

    return (
        f"Calling about {record.child_name}'s school fees, sir. "
        f"For {record.term_label}, the amount of {total} is due "
        f"by {record.fee_due_date}. May I help with any question?"
    )


def _closing(record: ParentRecord) -> str:
    voc = vocative(record)
    is_telugu = (record.language_preference or "").strip().lower() == "telugu"
    if is_telugu:
        return f"Dhanyavaadalu, Garu. Office vaaru follow up chestaaru. Have a peaceful day."
    return (
        f"Thank you {voc}. The office will follow up if needed. "
        f"Have a peaceful day, {voc}."
    )


SCENARIO = Scenario(
    scenario_id="fee_overdue_inquiry",
    objective=(
        "Confirm the parent received the reminder, address questions, "
        "share installment options if asked. Never pressure."
    ),
    opening_line=_opening,
    closing_line=_closing,
    posture_note=(
        "## Scenario: PATIENT INQUIRY (fees not yet paid)\n"
        "- Open by asking if they have any question about the fee.\n"
        "- If they say they will pay soon, accept gracefully: 'Thank you "
        "sir, I will inform the office.' Do not press for a specific date.\n"
        "- If they raise a financial concern, share installment options: "
        "'A 3-month EMI plan is available, no extra cost.'\n"
        "- If they ask about the consequences of late payment, be honest "
        "but gentle: 'The office can clarify if you need details, sir.' "
        "Do NOT recite policy from memory.\n"
        "- If they sound stressed, acknowledge: 'I understand sir. We are "
        "not in a hurry. The school is here to support {child}.' Replace "
        "{child} with the actual name from the verified record.\n"
        "- Close within 4-5 turns; do not extend the call once the parent "
        "has said they will follow up."
    ),
)
