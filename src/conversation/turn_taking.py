"""
Turn-Taking Engine
Manages the conversational floor: who speaks, when, and for how long.
Ref: SigArch 2026 [^16]; Sacks, Schegloff & Jefferson (1974) turn-taking theory.

Core principle: The AI does not TAKE the floor. It is GIVEN the floor
by the user's silence, gaze, or explicit invitation.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, List


class TurnState(Enum):
    """States of the conversational floor."""
    IDLE = auto()           # No one speaking
    USER_SPEAKING = auto()  # User has the floor
    AI_SPEAKING = auto()    # AI has the floor
    BOTH_SPEAKING = auto()  # Overlap (barge-in)
    TRANSITIONING = auto()  # Floor is changing hands


class UserReadiness(Enum):
    """How ready the user is to receive information."""
    UNAVAILABLE = auto()    # User is speaking, driving, distracted
    PROCESSING = auto()     # User is silent but may still be thinking
    READY = auto()          # User is silent, attentive, inviting response
    EXPLICIT = auto()       # User explicitly asked for response ("what do you think?")


@dataclass
class TurnMetrics:
    """Metrics for a single conversational turn."""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: int = 0
    words_spoken: int = 0
    interruptions: int = 0
    pause_before_ms: int = 0


@dataclass
class TurnTakingConfig:
    """
    Configuration for turn-taking behavior.
    Ref: 300ms pause = turn-transition relevance place (Sacks et al. 1974).
    """
    # Silence thresholds
    min_user_pause_ms: int = 400       # Minimum silence before AI can take floor
    optimal_user_pause_ms: int = 800   # Optimal silence — user is done thinking
    max_user_pause_ms: int = 3000      # User has stopped; prompt gently

    # Barge-in detection
    barge_in_threshold_ms: int = 200   # User speech during AI speech = barge-in
    barge_in_grace_ms: int = 100       # Brief sounds (cough, breath) ignored

    # AI speaking constraints
    ai_max_turn_duration_ms: int = 8000   # AI shouldn't monologue > 8s
    ai_preferred_chunk_ms: int = 2000     # Preferred chunk size for back-and-forth
    ai_pause_between_chunks_ms: int = 300 # Pause to let user interject

    # Attentiveness
    backchannel_interval_ms: int = 3000   # "mm-hm" every 3s during long user turns
    acknowledgement_delay_ms: int = 150   # Brief pause before acknowledging

    # Experience/memory
    context_window_turns: int = 10        # How many turns to keep in active memory
    min_turns_before_summary: int = 5     # When to offer a recap


class TurnTakingEngine:
    """
    The conversational floor manager.

    Principle: The AI is a GUEST in the user's conversation.
    It waits to be invited. It leaves when asked. It does not overstay.
    """

    def __init__(self, config: TurnTakingConfig = None):
        self.config = config or TurnTakingConfig()
        self.state = TurnState.IDLE
        self.readiness = UserReadiness.UNAVAILABLE
        self.history: List[TurnMetrics] = []
        self.current_turn: Optional[TurnMetrics] = None
        self._last_user_speech_time: float = 0
        self._last_ai_speech_time: float = 0
        self._user_speaking_start: Optional[float] = None
        self._ai_speaking_start: Optional[float] = None
        self._barge_in_count: int = 0

    # -----------------------------------------------------------------------
    # Event handlers — called by the audio pipeline
    # -----------------------------------------------------------------------

    def on_user_speech_start(self) -> None:
        """User began speaking."""
        self._user_speaking_start = time.time()
        self._last_user_speech_time = self._user_speaking_start

        if self.state == TurnState.AI_SPEAKING:
            self.state = TurnState.BOTH_SPEAKING
            self._barge_in_count += 1
        else:
            self.state = TurnState.USER_SPEAKING

        self.readiness = UserReadiness.UNAVAILABLE

    def on_user_speech_end(self) -> None:
        """User stopped speaking."""
        now = time.time()
        if self._user_speaking_start:
            duration_ms = int((now - self._user_speaking_start) * 1000)
            self.current_turn = TurnMetrics(
                start_time=self._user_speaking_start,
                end_time=now,
                duration_ms=duration_ms,
            )
            self.history.append(self.current_turn)

        self._user_speaking_start = None
        self._last_user_speech_time = now

        if self.state == TurnState.BOTH_SPEAKING:
            # User stopped barge-in; AI may resume if appropriate
            self.state = TurnState.AI_SPEAKING
        else:
            self.state = TurnState.IDLE
            self.readiness = UserReadiness.PROCESSING

    def on_ai_speech_start(self) -> None:
        """AI began speaking."""
        self._ai_speaking_start = time.time()
        self._last_ai_speech_time = self._ai_speaking_start
        self.state = TurnState.AI_SPEAKING

    def on_ai_speech_end(self) -> None:
        """AI stopped speaking."""
        now = time.time()
        if self._ai_speaking_start:
            duration_ms = int((now - self._ai_speaking_start) * 1000)
            self.history.append(TurnMetrics(
                start_time=self._ai_speaking_start,
                end_time=now,
                duration_ms=duration_ms,
            ))
        self._ai_speaking_start = None
        self.state = TurnState.IDLE

    # -----------------------------------------------------------------------
    # Decision: Should the AI speak now?
    # -----------------------------------------------------------------------

    def should_ai_speak(self, has_response_ready: bool = False) -> bool:
        """
        The core question: is it the AI's turn?

        Returns True ONLY if:
        1. User is not speaking
        2. User has been silent long enough to indicate they're done
        3. AI has something to say
        4. User is in a receptive state
        """
        if not has_response_ready:
            return False

        if self.state in (TurnState.USER_SPEAKING, TurnState.BOTH_SPEAKING):
            return False  # User has the floor

        silence_ms = self._current_silence_ms()

        # Wait for minimum pause — user may just be breathing
        if silence_ms < self.config.min_user_pause_ms:
            return False

        # Optimal pause — user is done, inviting response
        if silence_ms >= self.config.optimal_user_pause_ms:
            self.readiness = UserReadiness.READY
            return True

        # Between min and optimal — check context
        if self._is_user_likely_done():
            return True

        return False

    def _current_silence_ms(self) -> int:
        """Milliseconds since last user speech ended."""
        if self._user_speaking_start is not None:
            return 0  # User is still speaking
        return int((time.time() - self._last_user_speech_time) * 1000)

    def _is_user_likely_done(self) -> bool:
        """
        Heuristics for whether a short pause means "I'm done" or "I'm thinking."
        """
        if not self.history:
            return True  # First turn; assume user is done

        # Look at user's typical turn length
        user_turns = [t for t in self.history if t.start_time > self._last_ai_speech_time]
        if not user_turns:
            return True

        avg_user_turn = sum(t.duration_ms for t in user_turns) / len(user_turns)
        last_turn = user_turns[-1].duration_ms

        # If last turn is >150% of average, user was likely finished a thought
        if last_turn > avg_user_turn * 1.5:
            return True

        # If last turn ended with a question word, user expects response
        # (This would be integrated with ASR transcript analysis)

        return False

    # -----------------------------------------------------------------------
    # Barge-in handling
    # -----------------------------------------------------------------------

    def was_barge_in(self) -> bool:
        """Did the user just interrupt the AI?"""
        return self._barge_in_count > 0 and self.state == TurnState.BOTH_SPEAKING

    def on_barge_in(self) -> dict:
        """
        Handle user interruption.
        Principle: When interrupted, STOP IMMEDIATELY. Do not finish your sentence.
        The user has something more important to say.
        """
        self._barge_in_count += 1

        # Determine barge-in type
        silence_before = self._current_silence_ms()

        if silence_before < self.config.barge_in_grace_ms:
            return {
                "action": "ignore",
                "reason": "brief_sound",
                "message": "Likely cough, breath, or ambient noise. Continue speaking.",
            }

        if self._barge_in_count > 2:
            return {
                "action": "yield_fully",
                "reason": "persistent_interruption",
                "message": "User has interrupted multiple times. Stop speaking. Listen fully.",
            }

        return {
            "action": "yield_and_listen",
            "reason": "user_has_floor",
            "message": "Stop speaking. Switch to listening. Resume only when invited.",
        }

    # -----------------------------------------------------------------------
    # Attentiveness signals
    # -----------------------------------------------------------------------

    def should_send_backchannel(self) -> bool:
        """
        Should the AI emit a backchannel signal ("mm-hm", "I see")?
        Only during long user turns to show attentiveness WITHOUT taking floor.
        """
        if self.state != TurnState.USER_SPEAKING:
            return False

        if not self._user_speaking_start:
            return False

        user_duration = int((time.time() - self._user_speaking_start) * 1000)

        # Only during long turns
        if user_duration < self.config.backchannel_interval_ms:
            return False

        # Don't backchannel too frequently
        if self.history and self.history[-1].interruptions > 0:
            return False

        return True

    def get_backchannel(self, user_emotion: str = "neutral") -> str:
        """
        Context-aware backchannel response.
        Must be short (<300ms), non-disruptive, and emotionally aligned.
        """
        channels = {
            "neutral": ["mm-hm", "I see", "got it", "okay"],
            "urgent": ["I'm here", "go ahead", "listening"],
            "distressed": ["I understand", "I'm with you", "take your time"],
            "confused": ["slow down", "say that again?", "I'm following"],
        }
        import random
        return random.choice(channels.get(user_emotion, channels["neutral"]))

    # -----------------------------------------------------------------------
    # Experience / memory
    # -----------------------------------------------------------------------

    def get_conversation_phase(self) -> str:
        """Determine where we are in the conversation lifecycle."""
        turn_count = len([t for t in self.history if t.duration_ms > 0])

        if turn_count == 0:
            return "opening"
        elif turn_count <= 3:
            return "exploration"
        elif turn_count <= self.config.min_turns_before_summary:
            return "deepening"
        elif turn_count >= self.config.context_window_turns:
            return "recap_needed"
        else:
            return "mature"

    def should_offer_summary(self) -> bool:
        """Has the conversation gone on long enough to need a recap?"""
        turn_count = len([t for t in self.history if t.duration_ms > 0])
        return turn_count >= self.config.min_turns_before_summary

    def get_stats(self) -> dict:
        """Conversation statistics for analytics."""
        user_turns = [t for t in self.history if t.start_time > self._last_ai_speech_time]
        ai_turns = [t for t in self.history if t.start_time <= self._last_ai_speech_time]

        return {
            "total_turns": len(self.history),
            "user_turns": len(user_turns),
            "ai_turns": len(ai_turns),
            "barge_ins": self._barge_in_count,
            "avg_user_turn_ms": sum(t.duration_ms for t in user_turns) / max(len(user_turns), 1),
            "avg_ai_turn_ms": sum(t.duration_ms for t in ai_turns) / max(len(ai_turns), 1),
            "current_state": self.state.name,
            "user_readiness": self.readiness.name,
        }


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
# [^33]: Silero Team. (2024). Silero VAD: Pre-trained enterprise-grade Voice Activity Detector.
# Sacks, H., Schegloff, E. A., & Jefferson, G. (1974). A Simplest Systematics for the Organization of Turn-Taking for Conversation. Language, 50(4), 696-735.
