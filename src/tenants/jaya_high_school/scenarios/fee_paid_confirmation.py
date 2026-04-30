"""
Scenario: Fee Paid In Full — Supportive Confirmation
=====================================================
Most common production flow. The parent has already paid for the
current term. Job: confirm warmly, thank, and close. Do NOT ask for
money. Do NOT pitch new courses. Aim for ≤4 turns end-to-end.
"""

from __future__ import annotations

from src.domains.education.parent_registry import ParentRecord
from src.tenants.jaya_high_school.honorifics import thanks, vocative
from src.tenants.jaya_high_school.scenarios.base import Scenario


def _opening(record: ParentRecord) -> str:
    """
    Scenario opening fires AFTER the parent's "Cheppandi" / "Yes" /
    invitation in turn 2. The greeting was just "Namaskaaram {name}
    Garu" — no intent stated yet — so this turn LEADS with the intent
    (Telangana phone-etiquette flow per user directive 2026-04-30).
    """
    is_telugu = (record.language_preference or "").strip().lower() == "telugu"
    last = record.payments[-1] if record.payments else None
    paid_str = f"₹{record.term_fee_total_inr:,}"

    if is_telugu:
        on_date = f" {last.date} na" if last else ""
        # Natural Telangana register per user feedback (2026-04-30):
        # use "X ayipoyindhi ani clarify cheyyadaniki call chesam, andi"
        # — past-tense "we called", "andi" politeness particle alternated
        # with "{name} garu" address. Avoids the textbook-formal feel of
        # "gurinchi call chesthunna" + repeated "Garu".
        return (
            f"{record.parent_name} garu, {record.child_name} school fees "
            f"ayipoyindhi ani clarify cheyyadaniki call chesam, andi. "
            f"Term fee {paid_str},{on_date} fully paid ayyindi. "
            f"Dhanyavaadalu mee prompt payment ki, andi."
        )

    on_date = f" on {last.date}" if last else ""
    return (
        f"Calling about {record.child_name}'s school fees, sir. "
        f"The term fee of {paid_str} has been received in full{on_date}. "
        "Thank you for your prompt payment."
    )


def _closing(record: ParentRecord) -> str:
    voc = vocative(record)
    is_telugu = (record.language_preference or "").strip().lower() == "telugu"
    if is_telugu:
        return f"Manchidi andi. Have a peaceful day."
    return f"{thanks(record)}, {voc}. Have a peaceful day, {voc}."


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


def _news_offer(record: ParentRecord) -> str:
    """
    Generic broader follow-up after the primary intent (and pivot, if
    any) lands. The agent surfaces 1-2 relevant upcoming events from
    the school news layer if the parent accepts.
    """
    return (
        f"Sir, would you like to know about anything happening "
        f"at school in the coming weeks?"
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
        "- **Default behaviour after the parent acknowledges (says thank you, "
        "okay, bye, etc.): CLOSE WARMLY and end the call.** Do not push "
        "additional topics. The call is theirs to extend; if they say "
        "'anything else?', 'by the way…', or ask a question, you may "
        "engage — but never proactively if they have not invited it.\n"
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
    post_intent_news_offer=_news_offer,
)
