"""
Runtime language detector for Indian language voice sessions.

Uses Unicode script ranges for high-confidence detection, with a
Tenglish keyword fallback when speakers romanize Telugu in ASCII.

Returns BCP-47 language codes compatible with Sarvam AI APIs.
"""
from __future__ import annotations

import re

# Unicode script ranges for Indian languages
_TELUGU_RANGE   = re.compile(r"[ఀ-౿]")
_DEVANAGARI     = re.compile(r"[ऀ-ॿ]")   # Hindi, Marathi, Nepali
_TAMIL          = re.compile(r"[஀-௿]")
_KANNADA        = re.compile(r"[ಀ-೿]")
_MALAYALAM      = re.compile(r"[ഀ-ൿ]")
_BENGALI        = re.compile(r"[ঀ-৿]")
_GURMUKHI       = re.compile(r"[਀-੿]")   # Punjabi

# Tenglish keywords: romanised Telugu words commonly used in code-switched speech.
# Covers conversational markers, greeting/farewell, numerals context, cities.
_TENGLISH_KEYWORDS: frozenset[str] = frozenset({
    # conversational markers
    "cheppandi", "cheppu", "cheppara", "cheptunna",
    "ayindi", "ayya", "avunu", "kaadu", "kaana",
    "oka nimisham", "nimisham",
    "enti", "enti ra", "antav", "ante",
    "ela undi", "ela",
    "namaskaram", "namaskar",
    "dhanyavaadalu", "dhanyavaad",
    "meeru", "mee",
    # place names / demonym signals
    "warangal", "karimnagar", "nalgonda", "guntur",
    "rajahmundry", "kurnool", "tirupati", "chittoor",
    "nandyal", "hyderabad",
    # informal address
    "babu", "anna", "akka", "garu",
    # explicit language markers
    "tenglish", "telugu lo", "telugu",
    # common Tenglish verb endings
    "cheyyandi", "cheyyi", "cheyyu",
    "pettu", "pettandi",
    "teesko", "teesuko",
    "pampinchu", "pampu",
})

# Minimum keyword matches to declare Tenglish (avoids false positives)
_TENGLISH_THRESHOLD = 1


def detect_language(text: str) -> str | None:
    """
    Detect the primary language of a short utterance.

    Priority:
      1. Unicode script detection (high confidence, one char is enough)
      2. Tenglish keyword heuristic (romanised Telugu in ASCII)
      3. Returns None if ambiguous

    Args:
        text: Raw transcript text from STT.

    Returns:
        BCP-47 language code ("te-IN", "hi-IN", etc.) or None.
    """
    if not text:
        return None

    # Script detection — ordered by project priority
    if _TELUGU_RANGE.search(text):
        return "te-IN"
    if _DEVANAGARI.search(text):
        return "hi-IN"
    if _TAMIL.search(text):
        return "ta-IN"
    if _KANNADA.search(text):
        return "kn-IN"
    if _MALAYALAM.search(text):
        return "ml-IN"
    if _BENGALI.search(text):
        return "bn-IN"
    if _GURMUKHI.search(text):
        return "pa-IN"

    # Tenglish keyword heuristic (case-insensitive)
    lower = text.lower()
    hits = sum(1 for kw in _TENGLISH_KEYWORDS if kw in lower)
    if hits >= _TENGLISH_THRESHOLD:
        return "te-IN"

    return None
