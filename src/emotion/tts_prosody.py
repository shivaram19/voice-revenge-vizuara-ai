"""
TTS Prosody Mapper — Deterministic emotion-to-voice mapping for Deepgram Aura.

Research Provenance:
    - Deepgram Aura-2 provides 40+ voices with distinct personality tags
      (e.g., "Empathetic, Clear, Calm", "Warm, Energetic, Caring") [^E12].
    - Aura-2 has "context-aware emotional prosody" that dynamically adjusts
      pacing and expression based on text context [^E13].
    - However, Deepgram Aura does NOT expose SSML, pitch, or rate parameters
      via the /speak endpoint [^E12]. The only direct control is voice model
      selection (speaker parameter) [^E12].
    - Burkhardt et al. (2023): even simple rule-based text adaptations
      (punctuation, emphasis markers) shape emotional perception
      (UAR 0.76 arousal, 0.43 valence) [^E7].
    - Milvus/Zilliz (2025-2026): punctuation directly influences TTS prosody —
      periods = longer pause + falling pitch; commas = shorter pause;
      ellipses = dramatic pause; exclamation marks = increased stress [^E14].
    - Yoon et al. (2022): GPT-3 emotion labels + TTS achieve MOS 3.92,
      proving text-based emotion signaling is viable even without
      explicit acoustic control [^E6].

Control strategy (hierarchy of determinism):
    1. Voice model selection — map emotion to best-matching Aura-2 voice
    2. Text prosody cues — inject punctuation, pacing markers, emphasis
    3. Fallback — raw text (Aura's context-aware prosody handles baseline)

[^E6]: Yoon et al. (2022). GPT-3 emotion labels for expressive TTS.
[^E7]: Burkhardt et al. (2023). Rule-based SSML adaptations. UAR 0.76 arousal.
[^E12]: Deepgram. (2025). Aura-2 Voice Documentation. https://developers.deepgram.com/docs/tts-models
[^E13]: Deepgram. (2026). Aura-2 context-aware emotional prosody. https://deepgram.com/learn/the-accuracy-tax-of-emotional-voices-in-tts
[^E14]: Milvus/Zilliz. (2025-2026). TTS Prosody and Punctuation FAQ.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

from src.emotion.profile import EmotionalTone


# ---------------------------------------------------------------------------
# 1. Voice model selection map
# Deepgram Aura-2 voices with personality tags that match emotional needs [^E12]
# ---------------------------------------------------------------------------
_EMOTION_VOICE_MAP: Dict[EmotionalTone, str] = {
    # [^E12]: harmonia = "Empathetic, Clear, Calm, Confident" — ideal for distress
    EmotionalTone.DISTRESSED: "aura-2-harmonia-en",
    # [^E12]: mars = "Smooth, Patient, Trustworthy, Baritone" — de-escalates anger
    EmotionalTone.ANGRY: "aura-2-mars-en",
    # [^E12]: pluto = "Smooth, Calm, Empathetic, Baritone" — grounds urgency
    EmotionalTone.URGENT: "aura-2-pluto-en",
    # [^E12]: athena = "Calm, Smooth, Professional" — clarity for confusion
    EmotionalTone.CONFUSED: "aura-2-athena-en",
    # [^E12]: thalia = "Clear, Confident, Energetic" — matches gratitude energy
    EmotionalTone.GRATEFUL: "aura-2-thalia-en",
    # [^E12]: luna = "Friendly, Natural, Engaging" — default warm conversational
    EmotionalTone.CALM: "aura-2-luna-en",
    # [^E12]: hera = "Smooth, Warm, Professional" — gentle for fatigue
    EmotionalTone.TIRED: "aura-2-hera-en",
    # [^E12]: callista = "Clear, Energetic, Professional, Smooth" — efficient for rushed
    EmotionalTone.RUSHED: "aura-2-callista-en",
    # [^E12]: harmonia = empathetic calming for frustration
    EmotionalTone.FRUSTRATED: "aura-2-harmonia-en",
}

_DEFAULT_VOICE = "aura-2-luna-en"  # [^E12]: luna is the default friendly voice


# ---------------------------------------------------------------------------
# 2. Text prosody cue injectors
# Punctuation and formatting manipulations that neural TTS interprets as
# prosodic instructions [^E14][^E7]
# ---------------------------------------------------------------------------

def _calm_cues(text: str) -> str:
    """Slow pacing: commas for pauses, periods for grounding [^E14]."""
    # Ensure sentence ends with period for falling pitch closure [^E14]
    text = text.strip()
    if text and text[-1] not in ".?!":
        text += "."
    return text


def _urgent_cues(text: str) -> str:
    """Direct, no-fluff: strip filler commas, keep periods firm [^E14]."""
    # Remove unnecessary pauses that slow delivery [^E14]
    text = re.sub(r",\s+(?=(?:however|but|so|therefore|additionally))", " ", text)
    text = text.strip()
    if text and text[-1] not in ".!":
        text += "."
    return text


def _empathetic_cues(text: str) -> str:
    """Warm pacing: ellipses for thoughtful pauses, gentle commas [^E14]."""
    text = text.strip()
    # Insert gentle pause after apology/validation phrases [^E7]
    text = re.sub(r"(I understand|I'm sorry|I hear you)([.])", r"\1...", text)
    if text and text[-1] not in ".":
        text += "."
    return text


def _confused_cues(text: str) -> str:
    """Clear segmentation: numbered steps, pause after each [^E14]."""
    text = text.strip()
    # Add comma pause before "first", "next", "finally" if missing [^E14]
    text = re.sub(r"(?<!,)\s+(First|Next|Then|Finally|Step)", r", \1", text)
    if text and text[-1] not in ".":
        text += "."
    return text


def _rushed_cues(text: str) -> str:
    """Minimal punctuation: only essential periods, no decorative pauses [^E14]."""
    text = text.strip()
    # Strip non-essential commas to increase perceived speed [^E14]
    text = re.sub(r",\s+", " ", text)
    if text and text[-1] not in ".":
        text += "."
    return text


# Map each emotion to its (voice_model, text_processor) pair
_EMOTION_PROSODY: Dict[EmotionalTone, Tuple[str, callable]] = {
    EmotionalTone.CALM:        (_EMOTION_VOICE_MAP[EmotionalTone.CALM],        _calm_cues),
    EmotionalTone.URGENT:      (_EMOTION_VOICE_MAP[EmotionalTone.URGENT],      _urgent_cues),
    EmotionalTone.FRUSTRATED:  (_EMOTION_VOICE_MAP[EmotionalTone.FRUSTRATED],  _empathetic_cues),
    EmotionalTone.CONFUSED:    (_EMOTION_VOICE_MAP[EmotionalTone.CONFUSED],    _confused_cues),
    EmotionalTone.GRATEFUL:    (_EMOTION_VOICE_MAP[EmotionalTone.GRATEFUL],    _calm_cues),
    EmotionalTone.ANGRY:       (_EMOTION_VOICE_MAP[EmotionalTone.ANGRY],       _empathetic_cues),
    EmotionalTone.RUSHED:      (_EMOTION_VOICE_MAP[EmotionalTone.RUSHED],      _rushed_cues),
    EmotionalTone.TIRED:       (_EMOTION_VOICE_MAP[EmotionalTone.TIRED],       _empathetic_cues),
    EmotionalTone.DISTRESSED:  (_EMOTION_VOICE_MAP[EmotionalTone.DISTRESSED],  _empathetic_cues),
}


class TTSProsodyMapper:
    """
    Maps emotional targets to Deepgram Aura-2 voice + text prosody cues.

    Deterministic contract:
        Input:  (text, target_emotion) → str, EmotionalTone
        Output: (adapted_text, voice_model) → str, str

    Every mapping is explicit; no learned parameters [^E7].
    """

    def __init__(self, default_voice: str = _DEFAULT_VOICE):
        self.default_voice = default_voice

    def map(self, text: str, target_tone: EmotionalTone) -> Tuple[str, str]:
        """
        Apply prosody adaptation to text and select voice model.

        Returns:
            (adapted_text, voice_model_name)
        """
        voice, processor = _EMOTION_PROSODY.get(
            target_tone,
            (self.default_voice, _calm_cues)  # [^E12]: safe fallback
        )
        adapted = processor(text)
        return adapted, voice

    def get_voice_for_tone(self, target_tone: EmotionalTone) -> str:
        """Voice-only lookup (for greeting or backchannel selection)."""
        return _EMOTION_VOICE_MAP.get(target_tone, self.default_voice)
