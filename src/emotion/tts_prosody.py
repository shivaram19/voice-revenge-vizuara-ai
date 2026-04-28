"""
TTS Prosody Mapper — Vācika-Abhinaya for Deepgram Aura.

Maps emotional targets and situational contexts to Deepgram Aura-2 voice
models and SSML prosody cues. Inspired by Bharata Muni's Nāṭyaśāstra:
speech as performance (vācika-abhinaya) where tone, pacing, and silence
carry emotional meaning (rasa).

Research Provenance:
    - Deepgram Aura-2 provides 40+ voices with distinct personality tags
      (e.g., "Empathetic, Clear, Calm", "Warm, Energetic, Caring") [^E12].
    - Aura-2 has "context-aware emotional prosody" that dynamically adjusts
      pacing and expression based on text context [^E13].
    - Deepgram Aura supports SSML: <speak>, <break>, <prosody> [^70].
    - Bharata Muni's Nāṭyaśāstra: vācika-abhinaya — speech as emotional
      expression through tone, tempo, and pause (mauna).
    - Vedic communication ethics: kāla-deśa-pātra — speech must fit time,
      place, and person. Mauna (silence) is a communicative act.
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
    1. Voice model selection — map emotion/situation to Aura-2 voice
    2. SSML prosody cues — <break>, <prosody rate/pitch> for pacing
    3. Text prosody cues — punctuation, pacing markers, emphasis
    4. Fallback — raw text (Aura's context-aware prosody handles baseline)

[^E6]: Yoon et al. (2022). GPT-3 emotion labels for expressive TTS.
[^E7]: Burkhardt et al. (2023). Rule-based SSML adaptations. UAR 0.76 arousal.
[^E12]: Deepgram. (2025). Aura-2 Voice Documentation.
[^E13]: Deepgram. (2026). Aura-2 context-aware emotional prosody.
[^E14]: Milvus/Zilliz. (2025-2026). TTS Prosody and Punctuation FAQ.
[^70]: Deepgram. (2024). Aura Text-to-Speech documentation.
"""

from __future__ import annotations

import re
from enum import Enum, auto
from typing import Dict, Tuple, Optional

from src.emotion.profile import EmotionalTone


# ---------------------------------------------------------------------------
# Situational Speech Modes (Kāla-Deśa-Pātra)
# Sanskrit principle: speech must fit time, place, and person.
# ---------------------------------------------------------------------------

class SpeechSituation(Enum):
    """Situational context for speech mode selection."""
    GREETING = auto()        # Ādara — respectful welcome
    INSTRUCTION = auto()     # Upadeśa — clear, measured teaching
    INTERRUPTED = auto()     # Saṃyama — yielding with grace
    COMPASSIONATE = auto()   # Karuṇā — empathetic, soft
    ENTHUSIASTIC = auto()    # Utsāha — energetic, bright
    CLOSING = auto()         # Maṅgala — warm, definitive farewell
    DEFAULT = auto()         # Śānta — calm, neutral


# ---------------------------------------------------------------------------
# 1. Voice model selection map
# Deepgram Aura-2 voices with personality tags matching emotional needs [^E12]
# ---------------------------------------------------------------------------
_EMOTION_VOICE_MAP: Dict[EmotionalTone, str] = {
    EmotionalTone.DISTRESSED: "aura-2-harmonia-en",   # Empathetic, Calm
    EmotionalTone.ANGRY:      "aura-2-mars-en",       # Patient, Trustworthy
    EmotionalTone.URGENT:     "aura-2-pluto-en",      # Calm, Empathetic
    EmotionalTone.CONFUSED:   "aura-2-athena-en",     # Calm, Professional
    EmotionalTone.GRATEFUL:   "aura-2-thalia-en",     # Clear, Confident
    EmotionalTone.CALM:       "aura-2-luna-en",       # Friendly, Natural
    EmotionalTone.TIRED:      "aura-2-hera-en",       # Smooth, Warm
    EmotionalTone.RUSHED:     "aura-2-callista-en",   # Clear, Energetic
    EmotionalTone.FRUSTRATED: "aura-2-harmonia-en",   # Empathetic, Calming
}

# Situational voice overrides (takes precedence over emotion)
_SITUATION_VOICE_MAP: Dict[SpeechSituation, str] = {
    SpeechSituation.GREETING:      "aura-2-harmonia-en",   # Warm welcome
    SpeechSituation.INSTRUCTION:   "aura-2-athena-en",     # Clear, professional
    SpeechSituation.INTERRUPTED:   "aura-2-harmonia-en",   # Soft, questioning
    SpeechSituation.COMPASSIONATE: "aura-2-arcas-en",      # Gentle, reassuring
    SpeechSituation.ENTHUSIASTIC:  "aura-2-helios-en",     # Bright, energetic
    SpeechSituation.CLOSING:       "aura-2-harmonia-en",   # Warm, definitive
    SpeechSituation.DEFAULT:       "aura-2-luna-en",       # Friendly, neutral
}

_DEFAULT_VOICE = "aura-2-luna-en"


# ---------------------------------------------------------------------------
# 2. SSML prosody generators
# Bharata Muni's vācika-abhinaya: speech as emotional performance.
# ---------------------------------------------------------------------------

def _ssml_break(ms: int) -> str:
    """SSML break tag for prosodic silence (mauna)."""
    return f'<break time="{ms}ms"/>'


def _ssml_prosody(text: str, rate: str = None, pitch: str = None, volume: str = None) -> str:
    """Wrap text in SSML <prosody> tag."""
    attrs = []
    if rate:
        attrs.append(f'rate="{rate}"')
    if pitch:
        attrs.append(f'pitch="{pitch}"')
    if volume:
        attrs.append(f'volume="{volume}"')
    if not attrs:
        return text
    attr_str = " ".join(attrs)
    return f'<prosody {attr_str}>{text}</prosody>'


def _greeting_ssml(text: str) -> str:
    """Ādara (respect): slower, warm, with respectful pause."""
    text = text.strip()
    # Add respectful pause after school name
    text = re.sub(r"(Jaya High School[^.]*\.)", r"\1 " + _ssml_break(300), text)
    text = _ssml_prosody(text, rate="slow", pitch="+5%")
    return text


def _instruction_ssml(text: str) -> str:
    """Upadeśa (instruction): clear, measured, with boundary pauses."""
    text = text.strip()
    # Pause before numbered lists or key points
    text = re.sub(r"(:\s*)", r": " + _ssml_break(200), text)
    text = re.sub(r"(,\s*and\s+)", r"," + _ssml_break(150) + r" and ", text)
    return text


def _interrupted_ssml(text: str) -> str:
    """Saṃyama (restraint): slow, questioning, humble."""
    text = text.strip()
    # Slow down significantly; questioning intonation
    text = _ssml_prosody(text, rate="x-slow", pitch="-5%")
    # Add humble pause before yielding
    if "?" in text:
        text = text.replace("?", "?" + _ssml_break(400))
    return text


def _compassionate_ssml(text: str) -> str:
    """Karuṇā (compassion): soft, slow, reassuring."""
    text = text.strip()
    text = _ssml_prosody(text, rate="slow", pitch="-5%", volume="soft")
    # Gentle pause after reassurance phrases
    text = re.sub(r"(don't worry|take your time|I understand)([.])",
                  r"\1..." + _ssml_break(300), text, flags=re.IGNORECASE)
    return text


def _enthusiastic_ssml(text: str) -> str:
    """Utsāha (enthusiasm): bright, energetic, confident."""
    text = text.strip()
    text = _ssml_prosody(text, rate="medium", pitch="+5%")
    return text


def _closing_ssml(text: str) -> str:
    """Maṅgala (auspicious): warm, slow, definitive blessing."""
    text = text.strip()
    # Blessing phrases get slower, warmer
    text = re.sub(r"(Thank you[^.]*\.)", r"\1 " + _ssml_break(300), text)
    text = re.sub(r"(shine|bless|prosper)([^.]*\.)",
                  _ssml_prosody(r"\1\2", rate="slow", pitch="+5%") + ".", text)
    text = _ssml_prosody(text, rate="slow")
    return text


# ---------------------------------------------------------------------------
# 3. Legacy text prosody cue injectors (punctuation-based)
# ---------------------------------------------------------------------------

def _calm_cues(text: str) -> str:
    """Slow pacing: commas for pauses, periods for grounding [^E14]."""
    text = text.strip()
    if text and text[-1] not in ".?!":

        text += "."
    return text


def _urgent_cues(text: str) -> str:
    """Direct, no-fluff: strip filler commas, keep periods firm [^E14]."""
    text = re.sub(r",\s+(?=(?:however|but|so|therefore|additionally))", " ", text)
    text = text.strip()
    if text and text[-1] not in ".!":
        text += "."
    return text


def _empathetic_cues(text: str) -> str:
    """Warm pacing: ellipses for thoughtful pauses, gentle commas [^E14]."""
    text = text.strip()
    text = re.sub(r"(I understand|I'm sorry|I hear you)([.])", r"\1...", text)
    if text and text[-1] not in ".":
        text += "."
    return text


def _confused_cues(text: str) -> str:
    """Clear segmentation: numbered steps, pause after each [^E14]."""
    text = text.strip()
    text = re.sub(r"(?!,)\s+(First|Next|Then|Finally|Step)", r", \1", text)
    if text and text[-1] not in ".":
        text += "."
    return text


def _rushed_cues(text: str) -> str:
    """Minimal punctuation: only essential periods, no decorative pauses [^E14]."""
    text = text.strip()
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

_SITUATION_SSML: Dict[SpeechSituation, callable] = {
    SpeechSituation.GREETING:      _greeting_ssml,
    SpeechSituation.INSTRUCTION:   _instruction_ssml,
    SpeechSituation.INTERRUPTED:   _interrupted_ssml,
    SpeechSituation.COMPASSIONATE: _compassionate_ssml,
    SpeechSituation.ENTHUSIASTIC:  _enthusiastic_ssml,
    SpeechSituation.CLOSING:       _closing_ssml,
    SpeechSituation.DEFAULT:       lambda t: t,
}


class TTSProsodyMapper:
    """
    Maps emotional targets and situational contexts to Deepgram Aura-2
    voice + SSML prosody cues. Inspired by Bharata Muni's vācika-abhinaya.

    Deterministic contract:
        Input:  (text, target_emotion, situation) → str, EmotionalTone, SpeechSituation
        Output: (adapted_text, voice_model, use_ssml) → str, str, bool
    """

    def __init__(self, default_voice: str = _DEFAULT_VOICE):
        self.default_voice = default_voice

    def map(
        self,
        text: str,
        target_tone: EmotionalTone,
        situation: SpeechSituation = SpeechSituation.DEFAULT,
    ) -> Tuple[str, str, bool]:
        """
        Apply prosody adaptation to text and select voice model.

        Returns:
            (adapted_text, voice_model_name, use_ssml)
        """
        # Situation overrides emotion for voice selection
        voice = _SITUATION_VOICE_MAP.get(situation)
        if voice is None:
            voice = _EMOTION_VOICE_MAP.get(target_tone, self.default_voice)

        # Apply emotion-based text cues (legacy punctuation)
        _, text_processor = _EMOTION_PROSODY.get(
            target_tone,
            (self.default_voice, _calm_cues)
        )
        adapted = text_processor(text)

        # Apply situation-based SSML
        ssml_processor = _SITUATION_SSML.get(situation, lambda t: t)
        adapted = ssml_processor(adapted)

        use_ssml = situation != SpeechSituation.DEFAULT
        return adapted, voice, use_ssml

    def get_voice_for_tone(self, target_tone: EmotionalTone) -> str:
        """Voice-only lookup (for greeting or backchannel selection)."""
        return _EMOTION_VOICE_MAP.get(target_tone, self.default_voice)


# References
# [^E6]: Yoon et al. (2022). GPT-3 emotion labels for expressive TTS.
# [^E7]: Burkhardt et al. (2023). Rule-based SSML adaptations.
# [^E12]: Deepgram. (2025). Aura-2 Voice Documentation.
# [^E13]: Deepgram. (2026). Aura-2 context-aware emotional prosody.
# [^E14]: Milvus/Zilliz. (2025-2026). TTS Prosody and Punctuation FAQ.
# [^70]: Deepgram. (2024). Aura Text-to-Speech documentation.
