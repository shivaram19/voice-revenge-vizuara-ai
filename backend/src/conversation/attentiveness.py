"""
Attentiveness Engine
The AI's ability to listen, understand readiness, and respond with respect.

Core principle: You cannot be attended to unless you are ready to attend.
The AI senses the user's cognitive, emotional, and situational readiness
before speaking. It does not broadcast. It does not interrupt. It waits.

Ref: Goffman (1967) on conversational rituals; Clark (1996) on joint activity;
SigArch 2026 on latency masking [^16].
"""

import time
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict


class AttentionState(Enum):
    """Where is the user's attention right now?"""
    UNKNOWN = auto()          # No signal yet
    FULLY_PRESENT = auto()    # User is silent, focused, waiting
    MULTITASKING = auto()     # User is talking but distracted
    THINKING = auto()         # User is silent but processing
    DISTRESSED = auto()       # User is upset, overwhelmed
    RUSHED = auto()           # User is in a hurry, wants brevity
    EXPLORATORY = auto()      # User is curious, wants detail


class EmotionalTone(Enum):
    """Detected emotional tone of the user."""
    CALM = auto()
    URGENT = auto()
    FRUSTRATED = auto()
    CONFUSED = auto()
    GRATEFUL = auto()
    ANGRY = auto()
    TIRED = auto()


@dataclass
class AttentivenessConfig:
    """Configuration for attentiveness behavior."""
    # Timing
    min_attention_window_ms: int = 500      # User needs at least 500ms to process
    thinking_grace_period_ms: int = 1200    # Extra time if user seems to be thinking
    distress_pause_ms: int = 2000           # Longer pause if user is upset

    # Backchannel
    backchannel_enabled: bool = True
    backchannel_max_per_turn: int = 3       # Don't overdo it
    backchannel_variety: bool = True        # Don't repeat the same sound

    # Acknowledgment
    acknowledgment_enabled: bool = True
    acknowledgment_phrases: List[str] = field(default_factory=lambda: [
        "I understand.",
        "I hear you.",
        "I'm with you.",
        "I see what you're saying.",
        "Got it.",
    ])

    # Respect signals
    respect_pauses: bool = True             # Pause before responding
    respect_interruptions: bool = True      # Always yield when interrupted
    respect_distress: bool = True           # Slow down when user is upset


@dataclass
class UserSignal:
    """A signal about the user's current state."""
    timestamp: float
    speech_duration_ms: int = 0
    silence_duration_ms: int = 0
    speech_rate_wpm: int = 0
    pitch_variation: float = 0.0            # 0 = monotone, high = emotional
    volume_db: float = 0.0
    transcript: str = ""
    detected_emotion: EmotionalTone = EmotionalTone.CALM


class AttentivenessEngine:
    """
    The AI's emotional and social intelligence.

    This is not about WHAT the AI says. It is about WHEN and HOW.
    It is the difference between a robot that talks and a partner who listens.
    """

    def __init__(self, config: AttentivenessConfig = None):
        self.config = config or AttentivenessConfig()
        self.signals: List[UserSignal] = []
        self.current_state = AttentionState.UNKNOWN
        self._last_backchannel_time: float = 0
        self._backchannel_count_this_turn: int = 0
        self._used_acknowledgments: List[str] = []

    # -----------------------------------------------------------------------
    # Signal processing
    # -----------------------------------------------------------------------

    def on_user_speech(self, transcript: str, duration_ms: int, **metrics):
        """Process user speech signal."""
        signal = UserSignal(
            timestamp=time.time(),
            transcript=transcript,
            speech_duration_ms=duration_ms,
            speech_rate_wpm=metrics.get("speech_rate", 0),
            pitch_variation=metrics.get("pitch_variation", 0.0),
            volume_db=metrics.get("volume_db", 0.0),
            detected_emotion=self._detect_emotion(transcript, metrics),
        )
        self.signals.append(signal)
        self._update_attention_state()

    def on_user_silence(self, duration_ms: int):
        """Process user silence signal."""
        if self.signals:
            self.signals[-1].silence_duration_ms = duration_ms
        self._update_attention_state()

    def _detect_emotion(self, transcript: str, metrics: dict) -> EmotionalTone:
        """
        Detect emotional tone from transcript and audio features.
        Production: integrate emotion recognition model.
        """
        text = transcript.lower()

        # Text-based heuristics
        urgency_words = ["emergency", "now", "immediately", "urgent", "asap", "hurry"]
        frustration_words = ["again", "always", "never", "ridiculous", "unacceptable", "angry", "mad", "pissed"]
        confusion_words = ["what", "how", "don't understand", "confused", "lost", "wait"]
        gratitude_words = ["thank", "appreciate", "grateful", "helpful", "great"]
        distress_words = ["flood", "fire", "broken", "leaking", "danger", "hurt", "scared"]

        if any(w in text for w in distress_words):
            return EmotionalTone.URGENT
        if any(w in text for w in frustration_words):
            return EmotionalTone.FRUSTRATED
        if any(w in text for w in confusion_words):
            return EmotionalTone.CONFUSED
        if any(w in text for w in urgency_words):
            return EmotionalTone.URGENT
        if any(w in text for w in gratitude_words):
            return EmotionalTone.GRATEFUL

        # Audio-based heuristics
        if metrics.get("pitch_variation", 0) > 0.7:
            return EmotionalTone.URGENT
        if metrics.get("volume_db", 0) > 80:
            return EmotionalTone.ANGRY
        if metrics.get("speech_rate", 150) > 200:
            return EmotionalTone.RUSHED

        return EmotionalTone.CALM

    def _update_attention_state(self):
        """Determine user's attention state from signal history."""
        if not self.signals:
            self.current_state = AttentionState.UNKNOWN
            return

        latest = self.signals[-1]

        # Distressed: emotional + urgent content
        if latest.detected_emotion in (EmotionalTone.ANGRY, EmotionalTone.URGENT):
            self.current_state = AttentionState.DISTRESSED
            return

        # Rushed: fast speech + short turns
        if latest.detected_emotion == EmotionalTone.RUSHED:
            self.current_state = AttentionState.RUSHED
            return

        # Thinking: silence after a question or complex statement
        if latest.silence_duration_ms > 800 and "?" in latest.transcript:
            self.current_state = AttentionState.THINKING
            return

        # Fully present: silence, calm, no multitasking signals
        if latest.silence_duration_ms > 500 and latest.detected_emotion == EmotionalTone.CALM:
            self.current_state = AttentionState.FULLY_PRESENT
            return

        # Exploratory: questions, curiosity words, slower speech
        curiosity_words = ["wonder", "curious", "tell me more", "how does", "what about"]
        if any(w in latest.transcript.lower() for w in curiosity_words):
            self.current_state = AttentionState.EXPLORATORY
            return

        # Multitasking: short responses, distracted tone
        if latest.speech_duration_ms < 1000 and latest.silence_duration_ms < 300:
            self.current_state = AttentionState.MULTITASKING
            return

        self.current_state = AttentionState.UNKNOWN

    # -----------------------------------------------------------------------
    # Response timing
    # -----------------------------------------------------------------------

    def get_optimal_response_delay_ms(self) -> int:
        """
        How long should the AI wait before responding?

        Principle: Match the user's rhythm.
        - Distressed user → longer pause (show you're not rushing them)
        - Rushed user → minimal pause (respect their time)
        - Thinking user → extra grace period (don't interrupt their thought)
        """
        base_delay = self.config.min_attention_window_ms

        if self.current_state == AttentionState.DISTRESSED:
            return base_delay + self.config.distress_pause_ms

        if self.current_state == AttentionState.RUSHED:
            return max(100, base_delay // 2)

        if self.current_state == AttentionState.THINKING:
            return base_delay + self.config.thinking_grace_period_ms

        if self.current_state == AttentionState.FULLY_PRESENT:
            return base_delay + 200  # Slight pause to show consideration

        return base_delay

    def should_respond_now(self, silence_ms: int) -> bool:
        """Has the user been silent long enough to indicate readiness?"""
        required = self.get_optimal_response_delay_ms()
        return silence_ms >= required

    # -----------------------------------------------------------------------
    # Backchannel generation
    # -----------------------------------------------------------------------

    def should_backchannel(self, user_speech_duration_ms: int) -> bool:
        """Should the AI emit a listening signal?"""
        if not self.config.backchannel_enabled:
            return False

        if self._backchannel_count_this_turn >= self.config.backchannel_max_per_turn:
            return False

        # Only during long user turns
        if user_speech_duration_ms < 3000:
            return False

        # Don't backchannel too frequently (min 2s apart)
        time_since_last = (time.time() - self._last_backchannel_time) * 1000
        if time_since_last < 2000:
            return False

        return True

    def get_backchannel(self) -> str:
        """Generate a contextually appropriate backchannel."""
        self._last_backchannel_time = time.time()
        self._backchannel_count_this_turn += 1

        # Emotion-aware backchannels
        backchannels = {
            EmotionalTone.CALM: ["mm-hm", "I see", "got it", "okay"],
            EmotionalTone.URGENT: ["I'm here", "go ahead", "I'm listening"],
            EmotionalTone.FRUSTRATED: ["I understand", "that sounds frustrating", "I'm with you"],
            EmotionalTone.CONFUSED: ["slow down", "I'm following", "say more"],
            EmotionalTone.GRATEFUL: ["of course", "happy to help", "absolutely"],
            EmotionalTone.ANGRY: ["I hear you", "I understand", "let's fix this"],
            EmotionalTone.TIRED: ["take your time", "I'm here", "no rush"],
        }

        pool = backchannels.get(self.current_emotion, backchannels[EmotionalTone.CALM])

        if self.config.backchannel_variety:
            # Don't repeat recent backchannels
            pool = [b for b in pool if b not in self._recent_backchannels()]
            if not pool:
                pool = backchannels[EmotionalTone.CALM]

        return random.choice(pool)

    def _recent_backchannels(self) -> List[str]:
        """Get backchannels used in the last 60 seconds."""
        cutoff = time.time() - 60
        return [s.transcript for s in self.signals if s.timestamp > cutoff and len(s.transcript) < 20]

    # -----------------------------------------------------------------------
    # Acknowledgment generation
    # -----------------------------------------------------------------------

    def get_acknowledgment(self, user_transcript: str) -> Optional[str]:
        """
        Generate an acknowledgment that the user was heard.
        Used after barge-in or before a complex response.
        """
        if not self.config.acknowledgment_enabled:
            return None

        # Don't acknowledge trivial things
        if len(user_transcript.strip()) < 5:
            return None

        # Emotion-aware acknowledgment
        if self.current_state == AttentionState.DISTRESSED:
            return "I understand this is urgent. Let me help right away."

        if self.current_state == AttentionState.RUSHED:
            return "Quick answer:"

        # Pick an unused acknowledgment
        available = [a for a in self.config.acknowledgment_phrases if a not in self._used_acknowledgments]
        if not available:
            available = self.config.acknowledgment_phrases
            self._used_acknowledgments = []

        choice = random.choice(available)
        self._used_acknowledgments.append(choice)
        return choice

    # -----------------------------------------------------------------------
    # Response shaping
    # -----------------------------------------------------------------------

    def shape_response(self, raw_response: str) -> str:
        """
        Adjust the AI's response based on user's attention state.
        This is not WHAT to say — it's HOW to say it.
        """
        if self.current_state == AttentionState.RUSHED:
            # User is in a hurry → be brief
            return self._condense_response(raw_response)

        if self.current_state == AttentionState.DISTRESSED:
            # User is upset → be calm, direct, solution-focused
            return self._calm_response(raw_response)

        if self.current_state == AttentionState.CONFUSED:
            # User is confused → be clearer, step-by-step
            return self._clarify_response(raw_response)

        if self.current_state == AttentionState.EXPLORATORY:
            # User is curious → be detailed, offer more information
            return raw_response  # Keep full detail

        return raw_response

    def _condense_response(self, text: str) -> str:
        """Condense a response for rushed users."""
        sentences = text.split(". ")
        if len(sentences) <= 2:
            return text
        # Take first sentence + concluding sentence
        return f"{sentences[0]}. {sentences[-1]}"

    def _calm_response(self, text: str) -> str:
        """Add calming framing for distressed users."""
        calm_openers = [
            "I understand this is stressful. ",
            "I'm here to help. ",
            "Let's work through this together. ",
        ]
        opener = random.choice(calm_openers)
        return f"{opener}{text}"

    def _clarify_response(self, text: str) -> str:
        """Add clarifying structure for confused users."""
        return f"Let me break this down. {text} Does that make sense?"

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def current_emotion(self) -> EmotionalTone:
        """Current detected emotion."""
        if not self.signals:
            return EmotionalTone.CALM
        return self.signals[-1].detected_emotion

    @property
    def is_user_distressed(self) -> bool:
        """Is the user in a distressed state?"""
        return self.current_state == AttentionState.DISTRESSED

    @property
    def is_user_rushed(self) -> bool:
        """Is the user in a hurry?"""
        return self.current_state == AttentionState.RUSHED

    def reset_turn(self):
        """Reset per-turn state."""
        self._backchannel_count_this_turn = 0

    def get_summary(self) -> Dict:
        """Get attentiveness summary for analytics."""
        if not self.signals:
            return {"state": "unknown", "emotion": "calm"}

        return {
            "current_state": self.current_state.name,
            "current_emotion": self.current_emotion.name,
            "total_signals": len(self.signals),
            "avg_speech_duration_ms": sum(s.speech_duration_ms for s in self.signals) / len(self.signals),
            "emotion_distribution": self._emotion_distribution(),
        }

    def _emotion_distribution(self) -> Dict[str, int]:
        """Count of each detected emotion."""
        dist = {}
        for s in self.signals:
            name = s.detected_emotion.name
            dist[name] = dist.get(name, 0) + 1
        return dist


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
# Goffman, E. (1967). Interaction Ritual: Essays in Face-to-Face Behavior.
# Clark, H. H. (1996). Using Language. Cambridge University Press.
