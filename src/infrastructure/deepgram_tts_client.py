"""
Deepgram Aura TTS Client
========================
Cloud text-to-speech using Deepgram Aura model.

Research Provenance:
    - Deepgram Aura achieves <200ms TTFB (time-to-first-byte) for
      streaming speech synthesis [^70].
    - Cloud TTS offloads compute from the agent controller, enabling
      higher concurrent call density on CPU-only containers [^9].
    - Piper TTS (local) achieves RTF ~0.3× on CPU, which saturates
      a 1-vCPU container at ~3 concurrent syntheses [^9].
    - For 10-20 concurrent calls, cloud TTS is essential.

Design:
    - Synchronous HTTP client (Deepgram /speak endpoint).
    - Returns raw audio bytes (MP3 or WAV) for pipeline consumption.
    - The pipeline resamples from Deepgram output (24kHz default)
      to 8kHz μ-law for Twilio.
"""

import os
from typing import Optional

import requests


class DeepgramTTSClient:
    """
    Deepgram Aura TTS client.

    Environment Variables:
        DEEPGRAM_API_KEY  - Deepgram API key

    Parameters:
        model    - TTS model (default: aura-asteria-en)
        encoding - Output encoding (default: linear16)
        sample_rate - Output sample rate in Hz (default: 24000)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "aura-asteria-en",
        encoding: str = "linear16",
        sample_rate: int = 24000,
    ):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY", "").strip()
        self.model = model
        self.encoding = encoding
        self.sample_rate = sample_rate
        self._url = "https://api.deepgram.com/v1/speak"

        if not self.api_key:
            raise ValueError("Deepgram API key required. Set DEEPGRAM_API_KEY.")

    def synthesize(self, text: str, model: str = None) -> bytes:
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize.
            model: Optional voice model override (e.g., "aura-2-harmonia-en")
                   for emotion-mapped voice selection [^E12].

        Returns raw audio bytes (16-bit PCM at self.sample_rate).
        """
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

        params = {
            "model": model or self.model,  # [^E12]: per-call emotion voice override
            "encoding": self.encoding,
            "sample_rate": self.sample_rate,
        }

        payload = {"text": text}

        # Deepgram /speak returns audio bytes directly.
        # Ref: Deepgram Aura API docs [^70].
        resp = requests.post(
            self._url,
            headers=headers,
            params=params,
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Deepgram TTS failed ({resp.status_code}): {resp.text}"
            )

        return resp.content


# References
# [^9]: Hansen, M. (2023). Piper: A fast, local neural text-to-speech system.
# [^70]: Deepgram. (2024). Aura Text-to-Speech documentation.
