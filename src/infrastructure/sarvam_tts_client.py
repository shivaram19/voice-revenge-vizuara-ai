"""
Sarvam Bulbul v3 TTS Client
============================
Cloud text-to-speech using Sarvam AI's Bulbul model — purpose-built
for Indian languages with first-class Telugu (te-IN) support and an
explicit telephony 8 kHz benchmark.

Why this adapter exists (per DFS-010 §3.2 + ADR-019):
    Deepgram Aura, our incumbent TTS, does NOT support Telugu and has
    no SSML on its roadmap [^DeepgramAuraDocs]. For Telugu-preference
    parents, Aura phonetically renders Telugu words via American/British
    English voices, producing the name-mishearing pattern observed in
    production calls 4–7 ("Aarav" → "Aera"). Bulbul v3 supports Telugu
    as a first-class target with 35+ voices, evaluated independently
    against ElevenLabs/Cartesia at telephony 8 kHz quality [^SarvamBulbul].

API contract:
    POST https://api.sarvam.ai/text-to-speech
    Headers:
        api-subscription-key: <SARVAM_API_KEY>
        Content-Type: application/json
    Body:
        text                    string  required
        target_language_code    string  required (BCP-47, e.g. "te-IN", "en-IN")
        model                   string  default "bulbul:v3"
        speaker                 string  default "shubh" (v3); we use "gokul" for warm male
        speech_sample_rate      string  one of "8000"/"16000"/"22050"/"24000"/"32000"/"44100"/"48000"
        pace                    float   default 1.0
        temperature             float   default 0.6
        output_audio_codec      string  "wav" returns standard WAV
    Response:
        {"request_id": str, "audios": [base64-encoded WAV strings]}
        Multiple chunks are concatenated in order.

The pipeline already expects WAV bytes from `tts.synthesize(...)` — see
`production_pipeline._synthesize_to_ulaw`'s `wave.open(io.BytesIO(...))`
call — so this adapter returns standard WAV bytes after base64 decode.

[^DeepgramAuraDocs]: developers.deepgram.com/docs/tts-models — no Telugu listed.
[^SarvamBulbul]: sarvam.ai/blogs/bulbul-v3 — telephony 8 kHz benchmark.
"""

from __future__ import annotations

import base64
import io
import os
import wave
from typing import Optional

import requests


_DEFAULT_ENDPOINT = "https://api.sarvam.ai/text-to-speech"
_DEFAULT_MODEL = "bulbul:v3"
# Default speaker for Telugu calls. "gokul" is a warm male voice in v3
# per the Bulbul speaker list; tenants can override via env or constructor.
_DEFAULT_SPEAKER = "gokul"
_DEFAULT_SAMPLE_RATE = 24000
_DEFAULT_TIMEOUT_S = 30


class SarvamTTSClient:
    """
    Sarvam Bulbul v3 TTS adapter.

    Conforms to the same `synthesize(text, model=None, ssml=False) -> bytes`
    shape as `DeepgramTTSClient` so a `TTSRouter` can swap them at runtime
    without the pipeline knowing which provider serves a given turn.

    Bulbul v3 does NOT support SSML, pitch, or loudness; the `ssml` and
    `model` kwargs are accepted for interface parity but ignored. SSML
    requirements should be expressed via `pace` and `temperature`
    constructor params instead, or by switching to a different speaker.

    Args:
        api_key: SARVAM_API_KEY. Loaded from env if omitted.
        target_language_code: BCP-47 — "te-IN" for Telugu (default), "en-IN"
            for Indian English. The pipeline composition root selects which
            instance to bind to which language preference.
        speaker: Voice to use. Defaults to "gokul" — see Bulbul v3 speaker
            roster in module docstring.
        speech_sample_rate: Output sample rate. Default 24 kHz to match
            Deepgram Aura's output rate, so the resampling code in the
            pipeline does not need a per-provider branch.
        pace: 0.5–2.0; default 1.0. Lower for slower speech (DFS-007 §6
            cites slower delivery as more dignified for Suryapet parents).
        temperature: 0.0–1.0; default 0.6 per Sarvam's recommended range.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        target_language_code: str = "te-IN",
        speaker: str = _DEFAULT_SPEAKER,
        speech_sample_rate: int = _DEFAULT_SAMPLE_RATE,
        pace: float = 1.0,
        temperature: float = 0.6,
        endpoint: str = _DEFAULT_ENDPOINT,
        timeout_s: int = _DEFAULT_TIMEOUT_S,
    ) -> None:
        self.api_key = (api_key or os.getenv("SARVAM_API_KEY", "")).strip()
        self.target_language_code = target_language_code
        self.speaker = speaker
        self.speech_sample_rate = int(speech_sample_rate)
        self.pace = float(pace)
        self.temperature = float(temperature)
        self.endpoint = endpoint
        self.timeout_s = int(timeout_s)

        if not self.api_key:
            raise ValueError(
                "Sarvam API key required. Set SARVAM_API_KEY env or pass "
                "api_key=... to the constructor."
            )

    def synthesize(
        self,
        text: str,
        model: Optional[str] = None,  # noqa: ARG002 (interface parity)
        ssml: bool = False,           # noqa: ARG002 (Bulbul v3 ignores)
    ) -> bytes:
        """
        Synthesize `text` to a single WAV byte-string.

        If Sarvam returns multiple WAV chunks (multi-segment synthesis),
        they are concatenated head-to-tail with the WAV header preserved
        from the first chunk and only the PCM frames appended from the
        rest. This produces a single playable WAV file that the
        pipeline's `_synthesize_to_ulaw` can resample as if it had come
        from a single-shot call.
        """
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "text": text,
            "target_language_code": self.target_language_code,
            "model": _DEFAULT_MODEL,
            "speaker": self.speaker,
            "speech_sample_rate": str(self.speech_sample_rate),
            "pace": self.pace,
            "temperature": self.temperature,
            "output_audio_codec": "wav",
        }

        resp = requests.post(
            self.endpoint,
            headers=headers,
            json=body,
            timeout=self.timeout_s,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Sarvam TTS failed ({resp.status_code}): {resp.text[:300]}"
            )

        payload = resp.json()
        audios = payload.get("audios") or []
        if not audios:
            raise RuntimeError(
                "Sarvam TTS returned no audio segments "
                f"(request_id={payload.get('request_id')!r})."
            )

        wav_chunks = [base64.b64decode(seg) for seg in audios]
        if len(wav_chunks) == 1:
            return wav_chunks[0]

        return _concat_wavs(wav_chunks)


def _concat_wavs(chunks: list[bytes]) -> bytes:
    """
    Concatenate multiple WAV byte-strings into one. Assumes all chunks
    share sample rate / channels / sample width. Header from first chunk
    is preserved; subsequent chunks contribute only their PCM frames.
    """
    if not chunks:
        return b""
    if len(chunks) == 1:
        return chunks[0]

    out_buf = io.BytesIO()
    with wave.open(io.BytesIO(chunks[0]), "rb") as first:
        n_channels = first.getnchannels()
        sample_width = first.getsampwidth()
        framerate = first.getframerate()
        all_frames = first.readframes(first.getnframes())

    for chunk in chunks[1:]:
        with wave.open(io.BytesIO(chunk), "rb") as w:
            all_frames += w.readframes(w.getnframes())

    with wave.open(out_buf, "wb") as out:
        out.setnchannels(n_channels)
        out.setsampwidth(sample_width)
        out.setframerate(framerate)
        out.writeframes(all_frames)

    return out_buf.getvalue()


__all__ = ["SarvamTTSClient"]
