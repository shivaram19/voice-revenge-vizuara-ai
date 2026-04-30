"""
Telangana-Telugu / English honorific helpers for the Jaya High School tenant.

Per DFS-010 §2.2 and DFS-011 §2, the agent addresses Telugu-preference
parents with:
  - `Namaskaaram` greeting (Telangana-formal, NOT generic `Namaste`)
  - `Garu` (గారు) suffix (universal honorific, gender-neutral)
  - `Dhanyavaadalu` close

DFS-011 specifically corrected an earlier drift toward Andhra/textbook
Telugu register; Suryapet parents speak Telangana Telugu, which uses
`Namaskaaram` not `Namaste` for formal phone-call openings.

English-preference parents continue to receive sir / madam / Thank you.

These helpers branch on `ParentRecord.language_preference`. They are
deliberately conservative: only Telugu loanwords that the existing
Aura English TTS can render acceptably are used; full Telugu
sentences are NOT introduced here (Option B / dual-TTS work in DFS-010
§5 covers that, and DFS-011 §3 documents the full set of register
items rejected for today's Aura-only path).

Ref: DFS-010 §2.2 (honorific system), §3.4 (safe Telugu loanword set);
     DFS-011 §2 (Telangana-correct greeting); §3 (rejected items + reasons).
"""

from __future__ import annotations

from src.domains.education.parent_registry import ParentRecord


def _is_telugu_pref(record: ParentRecord) -> bool:
    """Whether the record opts into Telugu honorifics + closings."""
    if record is None:
        return False
    pref = (record.language_preference or "").strip().lower()
    return pref == "telugu"


def address(record: ParentRecord) -> str:
    """
    Long-form name + honorific. Used inline when introducing the parent.
    'Mrs. Lakshmi Devi Garu' (Telugu pref) | 'Mr. Shiv Ram' (English pref).
    """
    base = f"{record.salutation} {record.parent_name}".strip()
    if _is_telugu_pref(record):
        return f"{base} Garu"
    return base


def vocative(record: ParentRecord) -> str:
    """
    Short vocative form for use at sentence boundaries:
    'Garu' (Telugu) | 'sir' (English; default).
    """
    return "Garu" if _is_telugu_pref(record) else "sir"


def greeting_word(record: ParentRecord) -> str:
    """
    Opening greeting word.

    Telugu-pref → 'Namaskaaram' (Telangana-formal phone register).
    English-pref → 'Namaste' (pan-Indian short form, OK for English-pref).

    Per DFS-011 §2: Suryapet parents are Telangana Telugu speakers;
    'Namaskaaram' is the regionally-appropriate formal greeting.
    'Namaste' (Hindi/Sanskrit register) reads as Andhra/north-Indian
    register and feels slightly off in this audience.
    """
    return "Namaskaaram" if _is_telugu_pref(record) else "Namaste"


def thanks(record: ParentRecord) -> str:
    """Telugu 'Dhanyavaadalu' or English 'Thank you'."""
    return "Dhanyavaadalu" if _is_telugu_pref(record) else "Thank you"


def peaceful_close(record: ParentRecord) -> str:
    """Closing benediction with the appropriate honorific."""
    if _is_telugu_pref(record):
        return "Have a peaceful day, Garu."
    return "Have a peaceful day, sir."


__all__ = ["address", "vocative", "greeting_word", "thanks", "peaceful_close"]
