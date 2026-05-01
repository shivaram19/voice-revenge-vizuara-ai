"""
Sarvam Bulbul v3 TTS Client
============================
Cloud text-to-speech for Indian languages using Sarvam AI Bulbul v3.
Drop-in replacement for DeepgramTTSClient when the tenant primary language
is not English (Telugu, Hindi, Tamil, Kannada, etc.).

API:
    POST https://api.sarvam.ai/text-to-speech
    Header: api-subscription-key: <SARVAM_API_KEY>
    Body:   { inputs, target_language_code, speaker, model,
              speech_sample_rate, pitch, pace, loudness }
    Return: { audios: [base64-encoded WAV] }

Design notes:
    - Returns a WAV at speech_sample_rate=22050 Hz (Sarvam native).
    - The production pipeline reads `w.getframerate()` from the WAV header
      and resamples dynamically, so no pipeline-side constant change is needed.
    - `synthesize()` signature matches DeepgramTTSClient so the pipeline
      treats both as interchangeable `tts` objects.

Ref: Sarvam AI Text-to-Speech API docs (https://docs.sarvam.ai).
     Trelo-voice voice_persona.py — Bulbul v3 speaker catalog.
"""

from __future__ import annotations

import base64
import os
from typing import Optional

import requests


# Bulbul v3 speaker catalog, keyed by (language, tone/gender).
# Source: https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/text-to-speech/how-to/change-the-speaker-voice
BULBUL_SPEAKERS: dict[str, dict] = {
    # Telugu — primary for Jaya High School, Suryapet
    "te-IN-female": {"speaker": "kavya",  "pace": 0.9},
    "te-IN-male":   {"speaker": "rohan",  "pace": 1.0},
    # Hindi
    "hi-IN-female": {"speaker": "priya",  "pace": 0.9},
    "hi-IN-male":   {"speaker": "aditya", "pace": 1.0},
    # Tamil
    "ta-IN-female": {"speaker": "pooja",  "pace": 0.9},
    "ta-IN-male":   {"speaker": "amit",   "pace": 1.0},
    # Kannada
    "kn-IN-female": {"speaker": "roopali","pace": 0.9},
    "kn-IN-male":   {"speaker": "manan",  "pace": 1.0},
    # Malayalam
    "ml-IN-female": {"speaker": "tanya",  "pace": 0.9},
    "ml-IN-male":   {"speaker": "sumit",  "pace": 1.0},
    # Bengali
    "bn-IN-female": {"speaker": "simran", "pace": 0.9},
    "bn-IN-male":   {"speaker": "dev",    "pace": 1.0},
    # English (Indian accent)
    "en-IN-female": {"speaker": "ritu",   "pace": 1.0},
    "en-IN-male":   {"speaker": "shubh",  "pace": 1.0},
}

_SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


class SarvamTTSClient:
    """
    Sarvam Bulbul v3 TTS client.

    Environment Variables:
        SARVAM_API_KEY  — Sarvam AI subscription key

    Parameters:
        language_code  — BCP-47 code, e.g. "te-IN"
        speaker        — Bulbul v3 speaker name; auto-resolved from language+gender if None
        gender         — "female" (default) or "male" for auto speaker selection
        sample_rate    — Output WAV sample rate (default 22050; Sarvam native)
        pace           — Speech rate multiplier (0.5–2.0, default 0.9 for Telugu)
        loudness       — Volume multiplier (0.5–2.0, default 1.0)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        language_code: str = "te-IN",
        speaker: Optional[str] = None,
        gender: str = "female",
        sample_rate: int = 22050,
        pace: float = 0.9,
        loudness: float = 1.0,
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "").strip()
        self.language_code = language_code
        self.sample_rate = sample_rate
        self.loudness = loudness

        # Resolve speaker + pace from catalog if not explicitly given
        catalog_key = f"{language_code}-{gender}"
        catalog = BULBUL_SPEAKERS.get(catalog_key, BULBUL_SPEAKERS["te-IN-female"])
        self.speaker = speaker or catalog["speaker"]
        self.pace = pace if pace != 0.9 else catalog.get("pace", 0.9)

        if not self.api_key:
            raise ValueError(
                "Sarvam API key required. Set SARVAM_API_KEY environment variable."
            )

    def synthesize(self, text: str, model: str = None, ssml: bool = False) -> bytes:
        """
        Synthesize text to speech using Sarvam Bulbul v3.

        Args:
            text:  Text to synthesize (plain text; SSML not supported by Sarvam).
            model: Ignored — Sarvam always uses bulbul:v3; present for interface compat.
            ssml:  Ignored — Sarvam does not accept SSML markup.

        Returns:
            Raw WAV bytes at self.sample_rate Hz, 16-bit linear PCM.
            Compatible with the production pipeline's wave.open() + ratecv path.
        """
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": [text],
            "target_language_code": self.language_code,
            "speaker": self.speaker,
            "model": "bulbul:v3",
            "speech_sample_rate": self.sample_rate,
            "enable_preprocessing": True,
            "pitch": 0,
            "pace": self.pace,
            "loudness": self.loudness,
        }

        resp = requests.post(
            _SARVAM_TTS_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Sarvam TTS failed ({resp.status_code}): {resp.text[:300]}"
            )

        data = resp.json()
        audios = data.get("audios") or []
        if not audios:
            raise RuntimeError("Sarvam TTS returned empty audios list")

        # Response is base64-encoded WAV
        return base64.b64decode(audios[0])


def make_sarvam_tts(
    language_code: str = "te-IN",
    gender: str = "female",
    api_key: Optional[str] = None,
) -> SarvamTTSClient:
    """Convenience factory — creates a SarvamTTSClient for a given language."""
    return SarvamTTSClient(
        api_key=api_key or os.getenv("SARVAM_API_KEY", ""),
        language_code=language_code,
        gender=gender,
    )
