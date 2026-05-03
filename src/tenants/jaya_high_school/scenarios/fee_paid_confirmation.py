"""
Scenario: Fee Paid In Full — Supportive Confirmation
=====================================================
Most common production flow. The parent has already paid for the
current term. Job: confirm warmly, thank, and close. Do NOT ask for
money. Do NOT pitch new courses. Aim for ≤4 turns end-to-end.

Ref: DFS-013 (telephone conversation structure for institutional calls);
     user ground-truth feedback 2026-05-02 (Shiv Ram, Suryapet).
"""

from __future__ import annotations

from src.domains.education.parent_registry import ParentRecord
from src.tenants.jaya_high_school.scenarios.base import Scenario


def _consent(record: ParentRecord) -> str:
    """
    Turn 2 (after parent says 'cheppandi'): ask permission before
    revealing the call's purpose.

    Per user directive 2026-05-02: explicit consent-seeking.
    """
    return "Is this a good time to talk to you, sir?"


def _intent_summary(record: ParentRecord) -> str:
    """
    Turn 4 (after parent confirms a good time): state the fee status
    and purpose in one concise sentence.

    Per user directive 2026-05-02: natural spoken Telangana register.
    "kattesaru" = honorific past "have paid."
    """
    paid_str = f"₹{record.term_fee_total_inr:,}"
    return (
        f"Aarav term one fees kattesaru, "
        f"confirm cheyyadaniki call chesam, sir."
    )


def _intent_details(record: ParentRecord) -> str:
    """
    Optional follow-up — fired ONLY if the parent ASKS for specifics
    ("how much?" / "kuda enti?" / "eppudu?").
    """
    last = record.payments[-1] if record.payments else None
    if last:
        return f"{last.date} na {last.method} lo kattesaru, sir."
    return "Paid in full, sir."


def _opening(record: ParentRecord) -> str:
    """Backwards-compat full opening (summary + details)."""
    return f"{_intent_summary(record)} {_intent_details(record)}"


def _closing(record: ParentRecord) -> str:
    """
    Closing — offer contact, then warm close, then hang up.

    Per user directive 2026-05-02:
    "In case of any queries, contact Jaya High School, sir.
    Have a peaceful day, sir. Bye."
    """
    return (
        "In case of any queries, contact Jaya High School, sir. "
        "Have a peaceful day, sir. Bye."
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
        "Confirm that the parent's term fees of ₹15,000 are settled, "
        "offer the school contact for queries, and close warmly. "
        "Keep it concise.  No new asks."
    ),
    opening_line=_opening,
    closing_line=_closing,
    consent_line=_consent,
    posture_note=(
        "## Scenario: SUPPORTIVE CONFIRMATION (fees paid in full)\n"
        "- The parent has paid in full (₹15,000). The call is purely a "
        "courtesy confirmation — the school wants the parent to *know* "
        "the record is clear.\n"
        "- **Turn 1 (greeting):** 'Namaskaaram sir, nenu Jaya High School "
        "nunchi matlardhanam, Shivaram garu.'\n"
        "- **Turn 2 (parent):** 'Cheppandi' / 'Haan' / 'Yes' — the "
        "parent invites us to speak.\n"
        "- **Turn 3 (consent):** Ask 'Is this a good time to talk to you, sir?' "
        "WAIT for the parent to say yes. Do NOT state the intent yet.\n"
        "- **Turn 4 (parent):** 'Yes' / 'Haan' / 'Sare' — consent given.\n"
        "- **Turn 5 (intent):** State: 'Aarav term one fees kattesaru, "
        "confirm cheyyadaniki call chesam, sir.' Keep it to ONE sentence. "
        "Do NOT say 'thank you' before the parent has acknowledged anything.\n"
        "- **Turn 6 (parent):** 'Okay, thank you' — the parent acknowledges.\n"
        "- **Turn 7 (closing):** 'In case of any queries, contact Jaya High "
        "School, sir. Have a peaceful day, sir. Bye.'  Then END THE CALL "
        "from our side. Do not wait for the parent to say bye.\n"
        "- Use 'garu' ONLY in the greeting. Use 'sir' for the rest of the call.\n"
        "- Do NOT ask for any payment. Do NOT pitch new courses.\n"
        "- If the parent asks an unrelated question, answer briefly from FAQ "
        "knowledge if available, otherwise say the office will follow up."
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
