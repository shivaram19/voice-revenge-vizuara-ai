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


def _intent_summary(record: ParentRecord) -> str:
    """
    Turn 3: name + intent + thank-you tail (one sentence). The ground-
    truth Suryapet script (user directive 2026-04-30) collapses summary
    + thanks into a single agent turn — no separate "details" stage by
    default. After this, the agent waits ~3 seconds; if the parent
    doesn't respond, the auto-close fires.
    """
    is_telugu = (record.language_preference or "").strip().lower() == "telugu"
    if is_telugu:
        # Verbatim Suryapet register from telangana_actual_register memory.
        # "kattesaru" = honorific past "have paid"; more vernacular than
        # the earlier "ayipoyindhi" / "fully paid ayyindi" forms.
        # "term-1" is the user's verbatim term reference; ParentRecord
        # carries a date-range term_label, but parents speak in term
        # numbers ("term-1", "term-2"). For the Jaya HS deployment the
        # April-September block is term-1.
        return (
            f"{record.child_name} term-1 fees kattesaru ani confirm "
            f"cheyyadaniki call chesam sir. Thank you."
        )
    return (
        f"Calling to confirm {record.child_name} has paid the term fees, "
        "sir. Thank you."
    )


def _intent_details(record: ParentRecord) -> str:
    """
    Optional follow-up details — fired only if the parent ASKS for
    specifics ("how much?" / "kuda enti?"). The default Suryapet flow
    does not deliver these proactively; the parent is trusted to know.
    """
    is_telugu = (record.language_preference or "").strip().lower() == "telugu"
    last = record.payments[-1] if record.payments else None
    paid_str = f"₹{record.term_fee_total_inr:,}"
    if is_telugu:
        on_date = f", {last.date} na" if last else ""
        return (
            f"Term fee {paid_str}{on_date} kattesaru, sir."
        )
    on_date = f" on {last.date}" if last else ""
    return (
        f"The term fee was {paid_str}{on_date}, sir."
    )


def _opening(record: ParentRecord) -> str:
    """Backwards-compat full opening (summary + details)."""
    return f"{_intent_summary(record)} {_intent_details(record)}"


def _closing(record: ParentRecord) -> str:
    """
    Closing line, also used as the auto-close on 3-second silence after
    the summary. Verbatim from the user's ground-truth script
    (telangana_actual_register memory): "Thank you, have a peaceful
    day, good day, bye."
    """
    is_telugu = (record.language_preference or "").strip().lower() == "telugu"
    if is_telugu:
        return "Thank you, have a peaceful day. Good day, sir. Bye."
    return "Thank you. Have a peaceful day, sir. Bye."


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
    intent_summary=_intent_summary,
    intent_details=_intent_details,
)
