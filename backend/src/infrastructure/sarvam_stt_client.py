"""
Sarvam Saaras v3 STT Client
=============================
HTTP batch speech-to-text for Indian languages using Sarvam AI Saaras v3.

This client is used for **high-accuracy Telugu transcription** at turn-end,
complementing Deepgram streaming which handles real-time VAD and barge-in
detection. The two work together:

    Deepgram WebSocket  → VAD events + barge-in detection (language-agnostic)
    Sarvam Saaras v3    → Final turn transcription for Telugu accuracy

API:
    POST https://api.sarvam.ai/speech-to-text
    Header: api-subscription-key: <SARVAM_API_KEY>
    Body (multipart): file=<wav/mp3 bytes>, language_code, model, mode

Design notes:
    - `model="saaras:v3"` + `mode="codemix"` handles Tenglish (Telugu+English
      code-switching), which is the primary pattern at Jaya High School, Suryapet.
    - `language_code="unknown"` enables auto-detect across all 22 Indian languages.
    - Returns plain text transcript; confidence is best-effort from Sarvam.
    - Runs synchronously; callers should `asyncio.to_thread()` this in async code.

Ref: Sarvam AI STT docs (https://docs.sarvam.ai).
     ADR-002: Tiered ASR strategy.
"""

from __future__ import annotations

import io
import os
import wave
from typing import Optional

import requests


_SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"


class SarvamSTTClient:
    """
    Sarvam Saaras v3 HTTP STT client.

    Environment Variables:
        SARVAM_API_KEY — Sarvam AI subscription key

    Parameters:
        language_code — BCP-47 language code or "unknown" for auto-detect
        model         — Sarvam STT model (default: saaras:v3)
        mode          — "codemix" for mixed-language speech (Tenglish),
                        "formal" for clean formal Telugu
        sample_rate   — Input audio sample rate (default 8000 for Twilio PSTN)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        language_code: str = "unknown",   # auto-detect across 22 Indian languages
        model: str = "saaras:v3",
        mode: str = "codemix",            # handles Tenglish code-switching
        sample_rate: int = 8000,
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "").strip()
        self.language_code = language_code
        self.model = model
        self.mode = mode
        self.sample_rate = sample_rate

        if not self.api_key:
            raise ValueError(
                "Sarvam API key required. Set SARVAM_API_KEY environment variable."
            )

    def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: Optional[int] = None) -> str:
        """
        Transcribe raw PCM audio bytes (μ-law or linear16).

        Wraps the raw PCM in a WAV container before sending to Sarvam, since
        Sarvam requires a proper audio file rather than raw bytes.

        Args:
            pcm_bytes:   Raw audio bytes (linear16 PCM).
            sample_rate: Overrides self.sample_rate for this call.

        Returns:
            Transcribed text string (empty string if no speech detected).
        """
        sr = sample_rate or self.sample_rate

        # Wrap in WAV container
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)        # 16-bit
            wf.setframerate(sr)
            wf.writeframes(pcm_bytes)
        wav_bytes = wav_buffer.getvalue()

        return self._transcribe_wav(wav_bytes)

    def transcribe_wav(self, wav_bytes: bytes) -> str:
        """Transcribe a WAV file (already wrapped with headers)."""
        return self._transcribe_wav(wav_bytes)

    def _transcribe_wav(self, wav_bytes: bytes) -> str:
        headers = {
            "api-subscription-key": self.api_key,
        }

        files = {
            "file": ("audio.wav", io.BytesIO(wav_bytes), "audio/wav"),
        }

        data = {
            "language_code": self.language_code,
            "model": self.model,
            "mode": self.mode,
            "with_timestamps": "false",
        }

        resp = requests.post(
            _SARVAM_STT_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=30,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Sarvam STT failed ({resp.status_code}): {resp.text[:300]}"
            )

        result = resp.json()
        # Sarvam returns {"transcript": "...", "language_code": "te-IN", ...}
        return (result.get("transcript") or "").strip()

    def detect_language_from_audio(self, wav_bytes: bytes) -> Optional[str]:
        """
        Detect the spoken language from audio.
        Requires `language_code="unknown"` (auto-detect mode).
        Returns BCP-47 language code or None on failure.
        """
        headers = {"api-subscription-key": self.api_key}
        files = {"file": ("audio.wav", io.BytesIO(wav_bytes), "audio/wav")}
        data = {
            "language_code": "unknown",
            "model": self.model,
            "mode": self.mode,
            "with_timestamps": "false",
        }

        try:
            resp = requests.post(
                _SARVAM_STT_URL, headers=headers, files=files, data=data, timeout=30
            )
            if resp.status_code == 200:
                return resp.json().get("language_code")
        except Exception:
            pass
        return None
