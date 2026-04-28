"""
Emotion State Machine — Trajectory tracking and escalation detection.

Research Provenance:
    - GAUGE measures affective momentum using EMA over token-level risk
      vectors; NRS (directional) and ARP (magnitude) together capture
      both velocity and depth of emotional escalation [^E5].
    - Park et al. (2025): harmful conversational outcomes emerge through
      gradual affective drift, not single toxic utterances [^E5].
    - arXiv:2604.02713 (2026): emotion pacing produces reproducible
      escalation trajectories across turns 1-3, peaking at turn 3-4,
      proving 3-turn windows are psychologically valid [^E9].
    - TechRxiv LLMSER: sliding window + weighted averaging prevents
      overreaction to temporary mood fluctuations [^E4].
    - Tang et al. (2025, cited in arXiv:2604.02713): stance is dynamic,
      manifested incrementally through tone and emphasis across turns.

[^E4]: TechRxiv. (2025). LLMSER: Emotion-Enhanced LLM Responses.
[^E5]: Park, J., Afroogh, S., & Jiao, J. (2025). GAUGE. arXiv:2512.06193.
[^E9]: arXiv:2604.02713. (2026). Breakdowns in Conversational AI: Emotion Pacing Dynamics.
"""

from __future__ import annotations

from typing import Optional, Dict

from src.emotion.profile import (
    EmotionProfile,
    EmotionWindow,
    EmotionTrajectory,
    EmotionalTone,
)


class EmotionStateMachine:
    """
    Tracks emotional trajectory across a conversation session.

    Responsibilities:
        1. Maintain sliding window of EmotionProfiles
        2. Compute smoothed valence/arousal (EMA)
        3. Detect escalation (3+ consecutive negative turns) [^E9]
        4. Emit escalation alerts for upstream routing (human handoff)
        5. Provide trajectory-aware context for prompt adaptation

    Design: All thresholds are constructor parameters for auditability [^E5].
    """

    def __init__(
        self,
        window_size: int = 5,                        # [^E4]: 5-turn emotional memory
        escalation_threshold: int = 3,               # [^E9]: 3-turn escalation pattern validated psychologically
        negative_valence_threshold: float = -0.3,    # [^E1]: Russell circumplex negative-pleasant boundary
        fluctuation_variance_threshold: float = 0.25,# [^E4]: variance >0.25 = unstable emotional state
    ):
        self.window = EmotionWindow(max_size=window_size)
        self.escalation_threshold = escalation_threshold
        self.negative_valence_threshold = negative_valence_threshold
        self.fluctuation_variance_threshold = fluctuation_variance_threshold
        self._escalation_alerted: bool = False       # [^E5]: latch to prevent repeated alerts

    # -----------------------------------------------------------------------
    # Signal ingestion
    # -----------------------------------------------------------------------

    def on_turn(self, profile: EmotionProfile) -> None:
        """Process a new emotional reading from the current turn."""
        self.window.append(profile)

    # -----------------------------------------------------------------------
    # Escalation detection
    # -----------------------------------------------------------------------

    @property
    def is_escalating(self) -> bool:
        """True if user emotion is worsening across multiple turns [^E5]."""
        return self.window.trajectory == EmotionTrajectory.ESCALATING

    @property
    def should_alert_escalation(self) -> bool:
        """
        True ONCE when consecutive negative turns exceed threshold [^E9].
        Latches after first alert to avoid nagging the user.
        """
        if self._escalation_alerted:
            return False
        if self.window.consecutive_negative_turns >= self.escalation_threshold:
            self._escalation_alerted = True
            return True
        return False

    @property
    def should_offer_human(self) -> bool:
        """
        Offer human transfer when user has been distressed/angry for
        multiple consecutive turns [^E9]. This is a safety guardrail.
        """
        return self.window.consecutive_negative_turns >= self.escalation_threshold

    # -----------------------------------------------------------------------
    # Trajectory-aware properties
    # -----------------------------------------------------------------------

    @property
    def smoothed_valence(self) -> float:
        """EMA-weighted valence; negative = user is unhappy [^E5]."""
        return self.window.smoothed_valence

    @property
    def smoothed_arousal(self) -> float:
        """EMA-weighted arousal; high = user is activated/agitated [^E5]."""
        return self.window.smoothed_arousal

    @property
    def trajectory(self) -> EmotionTrajectory:
        """Classified emotional arc [^E5]."""
        return self.window.trajectory

    @property
    def latest_tone(self) -> EmotionalTone:
        """Most recent detected tone."""
        latest = self.window.latest
        return latest.detected_tone if latest else EmotionalTone.CALM

    @property
    def latest_target_tone(self) -> EmotionalTone:
        """Recommended AI response tone for latest turn."""
        latest = self.window.latest
        return latest.target_tone if latest else EmotionalTone.CALM

    # -----------------------------------------------------------------------
    # Prompt context
    # -----------------------------------------------------------------------

    def to_prompt_context(self) -> str:
        """Generate emotion context string for LLM prompt injection [^E4]."""
        latest = self.window.latest
        if not latest:
            return ""
        parts = [latest.to_prompt_context()]
        if self.is_escalating:
            parts.append("[TRAJECTORY: ESCALATING]")   # [^E5]: flag momentum for prompt adapter
        if self.window.consecutive_negative_turns >= 2:
            parts.append(f"[CONSECUTIVE_NEGATIVE: {self.window.consecutive_negative_turns}]")
        return " ".join(parts)

    def get_summary(self) -> Dict[str, any]:
        """Analytics / observability summary."""
        return {
            **self.window.get_summary(),
            "escalation_alerted": self._escalation_alerted,
            "should_offer_human": self.should_offer_human,
        }
