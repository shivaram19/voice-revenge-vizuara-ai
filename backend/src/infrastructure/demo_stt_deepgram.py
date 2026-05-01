"""
Deepgram STT for Demo Pipeline
===============================
Wraps Deepgram Nova-3 for batch transcription of buffered call audio.
Nova-3 achieves WER improvements of 20-50% over Whisper on non-native
accents and noisy environments [^61].

Accent Adaptation:
    For Indian English callers, the `language=en-IN` BCP 47 tag biases
    the acoustic and language model toward Indian English phonetic
    patterns, improving transcription accuracy without altering
    orthography [^54][^55]. Deepgram Nova-3 explicitly supports en-IN
    as a first-class language option [^56].

    Javed et al. (Interspeech 2023) benchmarked Indian English ASR and
    found dialect-specific model priors reduce WER by 5-10% relative
    to generic English models on Indian-accented speech [^57].

    ISO 639-1 / BCP 47 tag composition: `en` (language) + `IN` (region)
    [^58]. Deepgram's API accepts BCP 47 tags directly in the `language`
    query parameter [^56].

Ref: Deepgram. (2024). Nova-3 Streaming ASR Documentation.
"""

import os
from pathlib import Path
from typing import Optional


class DemoSTTDeepgram:
    """
    Batch STT using Deepgram Nova-3 HTTP API.
    Falls back to faster-whisper if Deepgram key is unavailable.

    Language selection follows BCP 47 conventions [^58]:
        - "en"    : Generic global English (default)
        - "en-IN" : Indian English (biased acoustic model)
        - "en-GB" : British English
        - "en-US" : American English

    For Hindi-English code-switching, use "multi" (Nova-3 multilingual)
    instead of "en-IN" [^54].
    """

    def __init__(self, api_key: Optional[str] = None, language: str = "en-IN"):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY", "").strip()
        # BCP 47 language tag: "en-IN" biases Nova-3 acoustic model toward
        # Indian English pronunciation patterns [^54][^55][^56].
        self.language = language
        self._fallback = None

    def _get_fallback(self):
        if self._fallback is None:
            try:
                from faster_whisper import WhisperModel
                self._fallback = WhisperModel("tiny", device="cpu", compute_type="int8")
            except ImportError:
                # faster-whisper not installed in cloud containers;
                # rely solely on Deepgram Nova-3 [^61].
                self._fallback = False
        return self._fallback

    def transcribe(self, wav_path: str) -> str:
        if not self.api_key:
            # Fall back to faster-whisper
            model = self._get_fallback()
            if not model:
                return ""
            segments, _ = model.transcribe(wav_path, language="en", vad_filter=True)
            return " ".join(s.text.strip() for s in segments).strip()

        import requests

        url = "https://api.deepgram.com/v1/listen"
        headers = {"Authorization": f"Token {self.api_key}"}
        params = {
            "model": "nova-3",
            # language=en-IN: BCP 47 tag biases acoustic model toward Indian
            # English phonetics without altering American orthography [^54][^56].
            # Javed et al. (2023) show 5-10% WER reduction on Indian-accented
            # speech with dialect-specific priors [^57].
            "language": self.language,
            "punctuate": "true",
            "utterances": "true",
            "smart_format": "true",
        }

        with open(wav_path, "rb") as f:
            resp = requests.post(url, headers=headers, params=params, data=f, timeout=30)

        if resp.status_code != 200:
            print(f"[WARN] Deepgram STT failed ({resp.status_code}): {resp.text}")
            model = self._get_fallback()
            if not model:
                return ""
            segments, _ = model.transcribe(wav_path, language="en", vad_filter=True)
            return " ".join(s.text.strip() for s in segments).strip()

        data = resp.json()
        results = data.get("results", {})
        channels = results.get("channels", [{}])
        alternatives = channels[0].get("alternatives", [{}])
        transcript = alternatives[0].get("transcript", "").strip()

        # If Deepgram returns empty, try fallback
        if not transcript:
            model = self._get_fallback()
            if not model:
                return ""
            segments, _ = model.transcribe(wav_path, language="en", vad_filter=True)
            return " ".join(s.text.strip() for s in segments).strip()

        return transcript


# References
# [^54]: Deepgram. (n.d.). Language. Deepgram Docs. https://developers.deepgram.com/docs/language
# [^55]: Deepgram. (n.d.). Models & Languages Overview. Deepgram Docs. https://developers.deepgram.com/docs/models-languages-overview
# [^56]: Deepgram. (n.d.). Language Detection. Deepgram Docs. https://developers.deepgram.com/docs/language-detection
# [^57]: Javed, T., et al. (2023). Svarah: Evaluating English ASR Systems on Indian Accents. Proc. Interspeech 2023. https://www.isca-archive.org/interspeech_2023/javed23_interspeech.pdf
# [^58]: Phillips, A., & Davis, M. (2009). Tags for Identifying Languages. BCP 47, RFC 5646. IETF.
# [^61]: Deepgram. (2024). Nova-3 Model Documentation. https://developers.deepgram.com/docs/nova-3
