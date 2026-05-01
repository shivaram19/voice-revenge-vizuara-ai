"""
Emotion Profile — Immutable snapshot of a single-turn emotional state.

Research Provenance:
    - Emotion is not binary; it occupies a continuous space defined by
      valence (pleasant/unpleasant) and arousal (activated/calm) [^E1].
    - Russell (1980) circumplex model: emotions distribute on a 2D
      valence-arousal plane, enabling deterministic numeric comparison [^E1].
    - Plutchik's wheel provides discrete labels that map cleanly to
      the circumplex, making them machine-actionable [^E2].
    - EC-WISE maps text onto Plutchik categories using lexicon + synonym
      + embedding methods for lightweight real-time classification [^E3].

[^E1]: Russell, J. A. (1980). A circumplex model of affect. *Journal of Personality and Social Psychology*, 39(6), 1161–1178. https://doi.org/10.1037/h0077714
[^E2]: Plutchik, R. (2001). The nature of emotions. *American Scientist*, 89(4), 344–350.
[^E3]: Hawaii Knowledge Management. (2024). EC-WISE: Emotional Curiosity Framework. https://scholarspace.manoa.hawaii.edu/bitstreams/7a2b5777-5544-47f0-b3e5-30f8f8e917ea/download
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, List, Dict


class EmotionalTone(Enum):
    """Discrete emotional categories mapped to Plutchik's wheel [^E2]."""
    CALM = auto()       # neutral, baseline
    URGENT = auto()     # high arousal, negative valence (emergency)
    FRUSTRATED = auto() # moderate arousal, negative valence
    CONFUSED = auto()   # moderate arousal, neutral valence
    GRATEFUL = auto()   # moderate arousal, positive valence
    ANGRY = auto()      # high arousal, negative valence
    RUSHED = auto()     # high arousal, neutral valence
    TIRED = auto()      # low arousal, negative valence
    DISTRESSED = auto() # high arousal, strongly negative valence


@dataclass(frozen=True)
class EmotionProfile:
    """
    Immutable emotional state for a single conversational turn.

    Design rationale:
        - frozen=True guarantees referential transparency: once emitted,
          an EmotionProfile cannot be mutated, making the audit trail
          deterministic [^E4].
        - valence in [-1.0, +1.0] and arousal in [0.0, 1.0] map directly
          to Russell's circumplex, enabling numeric interpolation for
          smooth tone transitions [^E1].
        - target_tone tells the downstream TTS/prompt layer what emotion
          the AI should adopt in response (not what the user feels).

    [^E4]: TechRxiv. (2025). LLMSER: Stateful emotion memory prevents
           abrupt tone shifts in multi-turn dialogue.
           https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.174123778.82557359
    """
    detected_tone: EmotionalTone = EmotionalTone.CALM
    confidence: float = 1.0
    valence: float = 0.0
    arousal: float = 0.5
    target_tone: EmotionalTone = EmotionalTone.CALM
    target_valence: float = 0.0
    target_arousal: float = 0.5
    transcript_snippet: str = ""
    detection_method: str = "heuristic"
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_prompt_context(self) -> str:
        """Serialize to a short string for LLM prompt injection [^E4]."""
        return (
            f"[Emotion: {self.detected_tone.name}, confidence={self.confidence:.2f}, "
            f"valence={self.valence:+.1f}, arousal={self.arousal:.1f}]"
        )

    def to_log_dict(self) -> Dict[str, any]:
        """Flat dict for observability (RED metrics, trace logging)."""
        return {
            "detected_tone": self.detected_tone.name,
            "confidence": round(self.confidence, 3),
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "target_tone": self.target_tone.name,
            "detection_method": self.detection_method,
            "transcript_snippet": self.transcript_snippet[:80],
        }


class EmotionTrajectory(Enum):
    """Long-term emotional arc across multiple turns [^E5]."""
    STABLE = auto()
    ESCALATING = auto()
    DE_ESCALATING = auto()
    FLUCTUATING = auto()
    RECOVERED = auto()


@dataclass(frozen=True)
class EmotionState:
    """
    Immutable snapshot of emotion state exposed to the pipeline.
    Fixes Primitive Obsession: replaces raw Dict[str, Any] from
    get_emotion_state() with a typed contract [^F1][^M1].
    """
    latest_target_tone: EmotionalTone = EmotionalTone.CALM
    should_offer_human: bool = False


@dataclass
class EmotionWindow:
    """
    Sliding window of recent EmotionProfiles for trajectory analysis.

    Research basis:
        - GAUGE uses exponential moving average (EMA) over turn-level
          risk vectors to detect affective momentum [^E5].
        - A 5-turn window captures short-term emotional memory without
          over-weighting stale signals [^E4].
        - Weighted averaging prioritizes recent emotions while still
          considering past states, preventing overreaction to transient
          mood fluctuations [^E4].

    [^E5]: Park, J., Afroogh, S., & Jiao, J. (2025). GAUGE: Guarding Affective Utterance Generation Escalation. arXiv:2512.06193
    """
    max_size: int = 5
    _profiles: List[EmotionProfile] = field(default_factory=list)
    _weights: List[float] = field(default_factory=list)

    def __post_init__(self):
        """Pre-compute EMA decay weights: w_i = alpha(1-alpha)^(n-i) [^E5]."""
        alpha = 0.5
        for i in range(self.max_size):
            self._weights.append(alpha * ((1 - alpha) ** (self.max_size - 1 - i)))

    def append(self, profile: EmotionProfile) -> None:
        """Add profile; evict oldest if at capacity [^E4]."""
        self._profiles.append(profile)
        if len(self._profiles) > self.max_size:
            self._profiles.pop(0)

    @property
    def smoothed_valence(self) -> float:
        """EMA-weighted average valence across window [^E5]."""
        if not self._profiles:
            return 0.0
        active_weights = self._weights[-len(self._profiles):]
        total = sum(active_weights)
        weighted = sum(p.valence * w for p, w in zip(self._profiles, active_weights))
        return weighted / total if total > 0 else 0.0

    @property
    def smoothed_arousal(self) -> float:
        """EMA-weighted average arousal across window [^E5]."""
        if not self._profiles:
            return 0.5
        active_weights = self._weights[-len(self._profiles):]
        total = sum(active_weights)
        weighted = sum(p.arousal * w for p, w in zip(self._profiles, active_weights))
        return weighted / total if total > 0 else 0.5

    @property
    def trajectory(self) -> EmotionTrajectory:
        """Classify emotional arc using slope of smoothed valence [^E5]."""
        if len(self._profiles) < 3:
            return EmotionTrajectory.STABLE
        vals = [p.valence for p in self._profiles]
        slope = (vals[-1] - vals[0]) / max(len(vals) - 1, 1)
        if slope < -0.3:
            return EmotionTrajectory.ESCALATING
        if slope > 0.3:
            return EmotionTrajectory.DE_ESCALATING
        mean_v = sum(vals) / len(vals)
        variance = sum((v - mean_v) ** 2 for v in vals) / len(vals)
        if variance > 0.25:
            return EmotionTrajectory.FLUCTUATING
        if vals[0] < -0.3 and vals[-1] > -0.1:
            return EmotionTrajectory.RECOVERED
        return EmotionTrajectory.STABLE

    @property
    def consecutive_negative_turns(self) -> int:
        """Count trailing turns with valence < -0.3 [^E7]."""
        count = 0
        for p in reversed(self._profiles):
            if p.valence < -0.3:
                count += 1
            else:
                break
        return count

    @property
    def latest(self) -> Optional[EmotionProfile]:
        """Most recent profile, or None."""
        return self._profiles[-1] if self._profiles else None

    def get_summary(self) -> Dict[str, any]:
        """Analytics-friendly summary."""
        return {
            "window_size": len(self._profiles),
            "smoothed_valence": round(self.smoothed_valence, 3),
            "smoothed_arousal": round(self.smoothed_arousal, 3),
            "trajectory": self.trajectory.name,
            "consecutive_negative": self.consecutive_negative_turns,
            "latest_tone": self.latest.detected_tone.name if self.latest else "None",
        }
