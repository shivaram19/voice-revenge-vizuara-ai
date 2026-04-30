"""
Telugu / English honorific helpers for the Jaya High School tenant.

Per DFS-010 §2.2 and §6, the agent should address Telugu-preference
parents with the Garu (గారు) suffix and close warmly with
Dhanyavaadalu — both pronounceable by Aura's English voice without
sounding stilted, while signalling cultural register to the parent.

English-preference parents continue to receive sir / madam / Thank you.

The helpers branch on `ParentRecord.language_preference`. They are
deliberately conservative: only Telugu loanwords that the existing
Aura English TTS can render acceptably are used; full Telugu
sentences are NOT introduced here (Option B / dual-TTS work in DFS-010
§5 covers that).

Ref: DFS-010 §2.2 (honorific system), §3.4 (safe Telugu loanword set),
     §6 (concrete copy changes).
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


def thanks(record: ParentRecord) -> str:
    """Telugu 'Dhanyavaadalu' or English 'Thank you'."""
    return "Dhanyavaadalu" if _is_telugu_pref(record) else "Thank you"


def peaceful_close(record: ParentRecord) -> str:
    """Closing benediction with the appropriate honorific."""
    if _is_telugu_pref(record):
        return "Have a peaceful day, Garu."
    return "Have a peaceful day, sir."


__all__ = ["address", "vocative", "thanks", "peaceful_close"]
