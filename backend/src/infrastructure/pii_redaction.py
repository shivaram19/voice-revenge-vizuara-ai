"""
PII Redaction for Voice Agent Logs
====================================
Phone numbers, emails, and sensitive identifiers must never appear in
persistent logs. Redact at the point of emission (defense in depth).

Research Provenance:
    - Deepgram PII redaction: 90%+ accuracy on PCI, SSN, numbers [^27]
    - Microsoft Presidio: 50+ entity types, 49 languages [^26]
    - GDPR Article 5(1)(c): data minimization — only collect what's necessary
    - HIPAA §164.312(b): audit controls must record access, not content

Ref: docs/principles/research-first-covenant.md
"""

from __future__ import annotations

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_PHONE_PATTERNS = [
    re.compile(
        r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
    ),  # International
    re.compile(r"\b\d{10}\b"),  # 10-digit Indian / US bare
    re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),  # US formatted
]

_CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_SSN_PATTERN = re.compile(r"\b\d{3}[-]?\d{2}[-]?\d{4}\b")
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)


# ---------------------------------------------------------------------------
# Redaction helpers
# ---------------------------------------------------------------------------

def redact_phone(value: Optional[str]) -> str:
    """
    Redact a phone number to last-4 digits.
    E.g. +91 89192 30290 → ***-0290
    """
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 10:
        return f"***-{digits[-4:]}"
    return "[REDACTED]"


def redact_text(text: str) -> str:
    """
    Redact PII from arbitrary text (transcripts, prompts, logs).
    Replaces with category labels so context is preserved for debugging.
    """
    if not text:
        return text

    text = _CREDIT_CARD_PATTERN.sub("[CREDIT_CARD]", text)
    text = _SSN_PATTERN.sub("[SSN]", text)
    text = _EMAIL_PATTERN.sub("[EMAIL]", text)

    for pattern in _PHONE_PATTERNS:
        text = pattern.sub("[PHONE]", text)

    return text


# References
# [^26]: Hamming AI. (2026). PII Redaction for Voice Agents.
# [^27]: Deepgram. (2026). PII Redaction Developer Guide.
