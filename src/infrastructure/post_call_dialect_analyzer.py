"""
Post-Call Dialect Analyzer
==========================
After a call ends, analyzes the conversation transcript to extract
dialect markers from the parent's speech. Updates the regional
pronunciation corpus so future calls to the same region sound more
authentic.

Flow:
    Call ends → Transcript saved → Analyzer runs → Extract markers
    → Compare against current profile → Suggest updates → Save corpus

Output:
    - dialect_corpus/{region_tag}/corpus.jsonl  (append-only)
    - dialect_corpus/{region_tag}/suggested_updates.json  (proposed word maps)

Ref: User directive 2026-05-02 (post-call reflection and dialect mapping).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DialectExtraction:
    """One extracted dialect marker from a call transcript."""
    call_sid: str
    region_tag: str
    parent_word: str
    context_phrase: str
    confidence: float  # 0.0–1.0
    turn_number: int


class PostCallDialectAnalyzer:
    """
    Analyzes call transcripts after the call ends.
    """

    def __init__(self, corpus_dir: Optional[str] = None) -> None:
        self.corpus_dir = Path(
            corpus_dir or os.getenv("DIALECT_CORPUS_DIR", "./dialect_corpus")
        )
        self.corpus_dir.mkdir(parents=True, exist_ok=True)

    def analyze(
        self,
        call_sid: str,
        region_tag: str,
        transcript: List[Dict[str, str]],
    ) -> List[DialectExtraction]:
        """
        Analyze a call transcript and extract dialect markers.

        Args:
            call_sid: Twilio CallSid for tracking.
            region_tag: Detected region (e.g., "suryapet").
            transcript: List of turn dicts, e.g.:
                [{"role": "assistant", "text": "Namaskaaram sir..."},
                 {"role": "user", "text": "Cheppandi..."}]

        Returns:
            List of extracted dialect markers.
        """
        extractions: List[DialectExtraction] = []

        # Load current profile to know what we're comparing against
        from src.infrastructure.dialect_router import get_dialect_router

        router = get_dialect_router()
        profile = router.get_profile(region_tag)
        known_words = set(profile.word_map.keys()) | set(profile.word_map.values())
        known_fillers = set(profile.filler_words)
        known_honorifics = set(profile.honorifics)

        for i, turn in enumerate(transcript):
            if turn.get("role") != "user":
                continue

            text = turn.get("text", "").lower()
            words = text.split()

            for word in words:
                word_clean = word.strip(".,!?;:")
                if not word_clean:
                    continue

                # Skip if already in known corpus
                if word_clean in known_words or word_clean in known_fillers:
                    continue

                # Heuristic: words that look like Telugu dialect variants
                # (end in specific suffixes, contain regional patterns)
                confidence = self._score_dialect_word(word_clean, region_tag)
                if confidence > 0.3:
                    extractions.append(
                        DialectExtraction(
                            call_sid=call_sid,
                            region_tag=region_tag,
                            parent_word=word_clean,
                            context_phrase=text[:100],
                            confidence=confidence,
                            turn_number=i,
                        )
                    )

        # Save to corpus
        self._save_extractions(region_tag, extractions)
        return extractions

    def _score_dialect_word(self, word: str, region_tag: str) -> float:
        """
        Heuristic scoring for how likely a word is a dialect marker.
        Higher = more likely to be region-specific.
        """
        score = 0.0

        # Telangana-specific suffixes
        if region_tag == "suryapet":
            if word.endswith("indhi") or word.endswith("indi"):
                score += 0.4
            if word.endswith("aru"):
                score += 0.3
            if word.endswith("andi"):
                score += 0.2
            if "ayipo" in word or "ayye" in word:
                score += 0.3

        # General: length and uniqueness
        if 3 <= len(word) <= 12:
            score += 0.1

        return min(score, 1.0)

    def _save_extractions(
        self, region_tag: str, extractions: List[DialectExtraction]
    ) -> None:
        if not extractions:
            return

        region_dir = self.corpus_dir / region_tag
        region_dir.mkdir(parents=True, exist_ok=True)

        corpus_path = region_dir / "corpus.jsonl"
        with corpus_path.open("a", encoding="utf-8") as f:
            for ex in extractions:
                f.write(json.dumps(asdict(ex), ensure_ascii=False) + "\n")

    def suggest_profile_updates(self, region_tag: str) -> Dict[str, str]:
        """
        Read the accumulated corpus for a region and suggest new word
        mappings based on frequency and confidence.

        Returns:
            Dict of proposed standard_word → regional_spoken_form.
        """
        region_dir = self.corpus_dir / region_tag
        corpus_path = region_dir / "corpus.jsonl"
        if not corpus_path.exists():
            return {}

        # Count occurrences
        word_counts: Dict[str, Dict[str, int]] = {}
        with corpus_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    word = obj.get("parent_word", "")
                    conf = obj.get("confidence", 0.0)
                    if word and conf > 0.5:
                        word_counts.setdefault(word, {"count": 0, "total_conf": 0.0})
                        word_counts[word]["count"] += 1
                        word_counts[word]["total_conf"] += conf
                except json.JSONDecodeError:
                    continue

        # Suggest mappings for words that appear 3+ times with high confidence
        suggestions: Dict[str, str] = {}
        for word, stats in word_counts.items():
            if stats["count"] >= 3:
                avg_conf = stats["total_conf"] / stats["count"]
                if avg_conf > 0.6:
                    # Suggest mapping: word stays as-is (we don't know the
                    # standard form yet — this requires human review)
                    suggestions[word] = word

        # Save suggestions
        if suggestions:
            suggest_path = region_dir / "suggested_updates.json"
            suggest_path.write_text(
                json.dumps(suggestions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return suggestions


_default_analyzer: Optional[PostCallDialectAnalyzer] = None


def get_analyzer() -> PostCallDialectAnalyzer:
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = PostCallDialectAnalyzer()
    return _default_analyzer


__all__ = ["DialectExtraction", "PostCallDialectAnalyzer", "get_analyzer"]
