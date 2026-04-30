"""
Scenario: Admission Status / Inquiry Follow-Up
================================================
For follow-up calls to families who have applied or shown interest in
admission. Job: confirm or update them on their application, schedule
a campus visit if helpful, answer questions about the school. NOT a
sales call — informational and respectful.
"""

from __future__ import annotations

from src.domains.education.parent_registry import ParentRecord
from src.tenants.jaya_high_school.honorifics import thanks, vocative
from src.tenants.jaya_high_school.scenarios.base import Scenario


def _opening(record: ParentRecord) -> str:
    """Lead with intent (turn 3 of the cheppandi-pattern flow)."""
    is_telugu = (record.language_preference or "").strip().lower() == "telugu"
    if is_telugu:
        return (
            f"{record.child_name} admission gurinchi call chesthunna, Garu. "
            f"Mee inquiry pi update share cheyalsi undi. Cheppanaa?"
        )
    return (
        f"Calling about {record.child_name}'s admission inquiry, sir. "
        f"May I share an update?"
    )


def _closing(record: ParentRecord) -> str:
    voc = vocative(record)
    is_telugu = (record.language_preference or "").strip().lower() == "telugu"
    if is_telugu:
        return (
            f"Dhanyavaadalu Jaya High School consider chesinanduku, Garu. "
            f"Mee child shine avvali. Have a peaceful day."
        )
    return (
        f"Thank you for considering Jaya High School, {voc}. "
        f"May your child shine. Have a peaceful day, {voc}."
    )


def _pivot(record: ParentRecord) -> str:
    """
    After the admission inquiry has been addressed, offer to share the
    school's brochure / admission packet via WhatsApp — easy to accept,
    easy to decline. Avoids extending the call unnecessarily.
    """
    return (
        f"Sir, would you like me to share our admission brochure "
        f"and fee structure on WhatsApp for your reference?"
    )


def _news_offer(record: ParentRecord) -> str:
    return (
        f"Sir, would you also like to hear about events happening "
        f"at school this month?"
    )


SCENARIO = Scenario(
    scenario_id="admission_inquiry",
    objective=(
        "Update the parent on their child's admission inquiry, offer a "
        "campus visit if appropriate, answer questions. Informational only."
    ),
    opening_line=_opening,
    closing_line=_closing,
    posture_note=(
        "## Scenario: ADMISSION INQUIRY UPDATE\n"
        "- This is NOT a sales call. Do not push the school. "
        "The parent has already shown interest by inquiring.\n"
        "- Share factual information from the verified record block: "
        "the child's name, the grade applied for, the application status "
        "if recorded. Do NOT invent dates or seat counts.\n"
        "- If the parent asks about the school, share details from "
        "FAQ knowledge — medium of instruction, hours, key strengths — "
        "in two-sentence answers.\n"
        "- Offer a campus visit if it would help: 'Sir, we welcome you "
        "to visit any weekday between 9 AM and 4 PM. Would Saturday "
        "morning suit you?' (offer ONE concrete time per turn.)\n"
        "- If the parent declines or wants to think, accept gracefully: "
        "'Of course, sir. Please call us anytime — we are here to help.'\n"
        "- Close with the dignified blessing: 'May your child shine.'"
    ),
    success_signals=(
        "thank you",
        "thanks",
        "okay sir",
        "i will visit",
        "i will think",
        "noted",
        "bye",
        "goodbye",
    ),
    post_intent_pivot=_pivot,
    post_intent_news_offer=_news_offer,
)
