"""
Dialect Router — Region-Scoped Pronunciation & Language Labeling
=================================================================
Detects the caller's regional dialect from their speech patterns and
routes both AI and parent audio through region-scoped pronunciation
profiles and caches.

Architecture:
    Parent speaks → DialectDetector extracts markers → RegionTag
    RegionTag → PronunciationProfile → Text transformation before TTS
    RegionTag + Text → RegionAudioCache → Scoped cache hit/miss
    Post-call → DialectAnalyzer → Update profile corpus

Regions supported (extensible):
    - suryapet       (Telangana, rural)
    - coastal-andhra (Andhra Pradesh, coastal)
    - rayalaseema    (Andhra Pradesh, inland)
    - hyderabad-urban (Telangana, urban Urdu-influenced)

Ref: User directive 2026-05-02 (dialect labeling and caching).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class DialectMarkers:
    """
    Extracted dialect markers from a single call transcript.
    Used to label the call and update the regional corpus.
    """
    region_tag: str
    detected_words: Dict[str, int] = field(default_factory=dict)
    filler_words: List[str] = field(default_factory=list)
    honorific_pattern: str = ""
    confidence_score: float = 0.0


@dataclass
class PronunciationProfile:
    """
    A region's pronunciation rules: standard word → spoken form.
    Also carries cultural context (fillers, honorifics, rhythm).
    """
    region_tag: str
    region_name: str
    language_code: str = "te-IN"
    # word → spoken form (e.g., "namaste" → "namaskaaram")
    word_map: Dict[str, str] = field(default_factory=dict)
    # Common filler words in this region (for detection)
    filler_words: List[str] = field(default_factory=list)
    # Honorific patterns (for detection and generation)
    honorifics: List[str] = field(default_factory=list)
    # Typical affirmative responses
    affirmatives: List[str] = field(default_factory=list)
    # Typical closing words
    closings: List[str] = field(default_factory=list)

    def apply(self, text: str) -> str:
        """
        Transform text through the pronunciation map.
        Case-insensitive exact-match replacement.
        """
        if not self.word_map:
            return text
        import re

        def _replace(m: "re.Match") -> str:
            token = m.group(0)
            lower = token.lower()
            if lower in self.word_map:
                return self.word_map[lower]
            return token

        # Match word boundaries
        return re.sub(r"\b\w+\b", _replace, text)


# ---------------------------------------------------------------------------
# Built-in profiles (seed data from user ground-truth)
# ---------------------------------------------------------------------------
_SURYAPET_PROFILE = PronunciationProfile(
    region_tag="suryapet",
    region_name="Suryapet, Telangana",
    language_code="te-IN",
    word_map={
        "namaste": "namaskaaram",
        "matladthunnam": "matladuthunnam",
        "matladutunnam": "matladuthunnam",
        "avunu": "avuna",
        "muginchindhi": "ayipoyindhi",
        "mugimpulu": "ayipoyindhi",
    },
    filler_words=["andi", "anta", "ante", "em", "endhukante"],
    honorifics=["garu", "sir", "andi"],
    affirmatives=["avuna", "haan", "sare", "ok", "yes"],
    closings=["bye", "have a peaceful day"],
)

_COASTAL_ANDHRA_PROFILE = PronunciationProfile(
    region_tag="coastal-andhra",
    region_name="Coastal Andhra Pradesh",
    language_code="te-IN",
    word_map={
        "namaskaaram": "namaste",
        "matlardhanam": "matladuthunnam",
        "avuna": "avunu",
        "ayipoyindhi": "muginchindhi",
    },
    filler_words=["andi", "anta", "ante", "mari"],
    honorifics=["garu", "sir", "andi"],
    affirmatives=["avunu", "haan", "sare", "ok"],
    closings=["bye", "have a nice day"],
)

_RAYALASEEMA_PROFILE = PronunciationProfile(
    region_tag="rayalaseema",
    region_name="Rayalaseema, Andhra Pradesh",
    language_code="te-IN",
    word_map={
        "namaskaaram": "namaskaram",
        "matlardhanam": "matladutunnam",
    },
    filler_words=["le", "ra", "andi"],
    honorifics=["garu", "sir", "ayya"],
    affirmatives=["avunu", "sare", "haan"],
    closings=["bye", "have a good day"],
)

_BUILTIN_PROFILES: Dict[str, PronunciationProfile] = {
    p.region_tag: p
    for p in [_SURYAPET_PROFILE, _COASTAL_ANDHRA_PROFILE, _RAYALASEEMA_PROFILE]
}


class DialectRouter:
    """
    Routes pronunciation and caching by detected region.
    """

    def __init__(self, custom_profiles_dir: Optional[str] = None) -> None:
        self._profiles: Dict[str, PronunciationProfile] = dict(_BUILTIN_PROFILES)
        self._custom_dir = Path(custom_profiles_dir) if custom_profiles_dir else None
        self._load_custom_profiles()

    def _load_custom_profiles(self) -> None:
        if not self._custom_dir or not self._custom_dir.exists():
            return
        for path in self._custom_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                profile = PronunciationProfile(**data)
                self._profiles[profile.region_tag] = profile
            except Exception:
                continue

    def get_profile(self, region_tag: str) -> PronunciationProfile:
        return self._profiles.get(region_tag, _SURYAPET_PROFILE)

    def detect_region_from_record(
        self, record: Optional[object]
    ) -> str:
        """
        Extract region tag from a ParentRecord.
        Falls back to 'suryapet' if no region data available.
        """
        if record is None:
            return "suryapet"
        # Try explicit region field first
        region = getattr(record, "region", None) or getattr(record, "location", None)
        if region:
            return str(region).lower().replace(" ", "-")
        # Fallback: infer from tenant
        tenant = getattr(record, "tenant_id", None)
        if tenant and "suryapet" in str(tenant).lower():
            return "suryapet"
        return "suryapet"

    def detect_region_from_transcript(
        self, transcript: str, current_region: str = "suryapet"
    ) -> str:
        """
        Analyze parent transcript for dialect markers.
        Returns the region with highest confidence.
        """
        text_lower = transcript.lower()
        scores: Dict[str, int] = {}

        for tag, profile in self._profiles.items():
            score = 0
            # Count matched words
            for word, spoken in profile.word_map.items():
                if word in text_lower or spoken in text_lower:
                    score += 2
            # Count filler words
            for filler in profile.filler_words:
                if filler in text_lower:
                    score += 1
            # Count honorifics
            for hon in profile.honorifics:
                if hon in text_lower:
                    score += 1
            scores[tag] = score

        if not scores:
            return current_region

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        # Only switch if confidence is high enough
        if scores[best] >= 3:
            return best
        return current_region

    def all_regions(self) -> List[str]:
        return list(self._profiles.keys())


# Singleton
_default_router: Optional[DialectRouter] = None


def get_dialect_router() -> DialectRouter:
    global _default_router
    if _default_router is None:
        _default_router = DialectRouter(
            custom_profiles_dir=os.getenv("DIALECT_PROFILES_DIR")
        )
    return _default_router


__all__ = [
    "DialectMarkers",
    "PronunciationProfile",
    "DialectRouter",
    "get_dialect_router",
]
