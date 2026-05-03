"""
IndicF5 TTS Client — Plug-and-Play Indian Language Voice Cloning
=================================================================
Zero-shot voice cloning for Telugu and 10 other Indian languages.
Loads ai4bharat/IndicF5 from HuggingFace with trust_remote_code.

Architecture:
    Text + Reference Audio + Reference Text → Diffusion TTS → WAV

Why IndicF5:
- Near-human MUSHRA scores for Telugu [Varadhan et al., 2025]
- Zero-shot cloning from 6-second reference clips
- Fully open-source (1.31 GB weights, MIT license)
- Backup to Sarvam Bulbul v3 if Sarvam enterprise clone is delayed

Ref: DFS-014 §4; VECL-TTS research track 2026-05-02.
"""

from __future__ import annotations

import io
import os
import wave
from typing import Optional

import numpy as np

# Lazy imports — transformers + torch are heavy; only load when needed
_TransformersModel = None
_SoundFile = None


def _lazy_imports():
    global _TransformersModel, _SoundFile
    if _TransformersModel is None:
        from transformers import AutoModel
        _TransformersModel = AutoModel
    if _SoundFile is None:
        import soundfile as sf
        _SoundFile = sf
    return _TransformersModel, _SoundFile


_DEFAULT_REPO = "ai4bharat/IndicF5"
_DEFAULT_SAMPLE_RATE = 24000


class IndicF5TTSClient:
    """
    IndicF5 adapter conforming to the same synthesize(...) → bytes
    interface as SarvamTTSClient and DeepgramTTSClient.

    Args:
        repo_id: HuggingFace model repo. Default ai4bharat/IndicF5.
        ref_audio_path: Path to reference audio for voice cloning.
                        If None, uses a default generic prompt from the repo.
        ref_text: Transcript of the reference audio. Must match exactly.
        device: "cuda" or "cpu". Defaults to cuda if available.
    """

    def __init__(
        self,
        repo_id: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.repo_id = (repo_id or os.getenv("INDICF5_REPO", _DEFAULT_REPO)).strip()
        self.ref_audio_path = (ref_audio_path or os.getenv("INDICF5_REF_AUDIO", "")).strip() or None
        self.ref_text = (ref_text or os.getenv("INDICF5_REF_TEXT", "")).strip() or None
        self.device = (device or os.getenv("INDICF5_DEVICE", "auto")).strip()

        self._model = None
        self._model_loaded = False

    def _load_model(self):
        if self._model_loaded:
            return
        AutoModel, _ = _lazy_imports()

        import torch

        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self._model = AutoModel.from_pretrained(
            self.repo_id,
            trust_remote_code=True,
        ).to(self.device)
        self._model.eval()
        self._model_loaded = True

    def synthesize(
        self,
        text: str,
        model: Optional[str] = None,  # noqa: ARG002
        ssml: bool = False,           # noqa: ARG002
        pace: Optional[float] = None,  # noqa: ARG002
        lang_pref: str = "",
    ) -> bytes:
        """
        Synthesize text to WAV bytes using IndicF5.

        Requires ref_audio_path and ref_text to be set for voice cloning.
        If not set, raises RuntimeError — IndicF5 cannot synthesize
        without a reference prompt.
        """
        if not self.ref_audio_path or not self.ref_text:
            raise RuntimeError(
                "IndicF5 requires a reference audio clip and its transcript. "
                "Set INDICF5_REF_AUDIO and INDICF5_REF_TEXT env vars, or "
                "pass ref_audio_path + ref_text to the constructor."
            )

        if not os.path.exists(self.ref_audio_path):
            raise RuntimeError(
                f"IndicF5 reference audio not found: {self.ref_audio_path}"
            )

        self._load_model()
        _, sf = _lazy_imports()

        with torch.no_grad():
            audio = self._model(
                text,
                ref_audio_path=self.ref_audio_path,
                ref_text=self.ref_text,
            )

        # Normalize to float32 if int16
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Wrap in WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)  # 16-bit
            w.setframerate(_DEFAULT_SAMPLE_RATE)
            # Convert float32 [-1, 1] to int16
            pcm = (audio * 32767).astype(np.int16)
            w.writeframes(pcm.tobytes())

        return buf.getvalue()


__all__ = ["IndicF5TTSClient"]
