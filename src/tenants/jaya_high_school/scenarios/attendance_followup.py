"""
Scenario: Attendance Follow-Up
================================
For calls placed when a child has been absent for several days without
the school having received an explanation. Job: gently check on the
child's wellbeing, capture the reason if shared, offer school support.
This is the most sensitive scenario — the family may be dealing with
illness, bereavement, or financial stress; the agent must lead with care.
"""

from __future__ import annotations

from src.domains.education.parent_registry import ParentRecord
from src.tenants.jaya_high_school.honorifics import thanks, vocative
from src.tenants.jaya_high_school.scenarios.base import Scenario


def _opening(record: ParentRecord) -> str:
    return (
        f"{thanks(record)} for taking the call, {vocative(record)}. "
        f"We have not seen {record.child_name} in school for a few days. "
        f"I just wanted to check — is everything alright at home?"
    )


def _closing(record: ParentRecord) -> str:
    voc = vocative(record)
    return (
        f"{thanks(record)} {voc}. We hope to see {record.child_name} back soon. "
        "Please feel free to call the office anytime. "
        f"Have a peaceful day, {voc}."
    )


SCENARIO = Scenario(
    scenario_id="attendance_followup",
    objective=(
        "Check on a child who has been absent. Lead with care for the "
        "family's wellbeing, capture the reason if offered, do NOT make "
        "the call about attendance compliance."
    ),
    opening_line=_opening,
    closing_line=_closing,
    posture_note=(
        "## Scenario: ATTENDANCE FOLLOW-UP (sensitive)\n"
        "- The child has been absent. Do NOT open with 'attendance is "
        "below requirement' or any compliance framing. Open with concern.\n"
        "- The family may be navigating illness, bereavement, financial "
        "stress, or a routine trip. Lead with care; let them tell you why.\n"
        "- If they share a reason — illness, family event, travel — "
        "acknowledge briefly: 'I am sorry to hear that, sir.' or 'I "
        "understand sir.' Do NOT probe for details.\n"
        "- If they share something serious (illness, bereavement), do NOT "
        "ask about fees, courses, or any school transactional matter. "
        "Offer: 'Please take whatever time you need, sir. The school is "
        "here whenever you are ready.'\n"
        "- If a homework / lesson catch-up question comes up: 'I will "
        "ask the class teacher to share notes, sir.' Do NOT promise "
        "specific arrangements you cannot make.\n"
        "- Never ask 'when will the child return' as a directive. If "
        "useful, ask gently: 'Is there anything we can help with from "
        "school, sir?'\n"
        "- Close with warmth, not policy."
    ),
    success_signals=(
        "thank you",
        "thanks",
        "okay sir",
        "we will come",
        "soon",
        "tomorrow",
        "next week",
        "noted",
        "bye",
        "goodbye",
    ),
)
