"""
Silero Neural VAD (ONNX)
========================
Production-grade voice activity detection using Silero's pre-trained
ONNX model. Processes 16kHz PCM with dual-threshold hysteresis.

Research Provenance:
    - Silero VAD achieves 96.4% accuracy at 16kHz [^10]
    - 8kHz direct input drops to 89.3% — resampling to 16kHz is mandatory [^10]
    - Dual-threshold hysteresis (0.5/0.35) reduces flapping at boundaries [^12]
    - ONNX Runtime inference: 1–5ms per frame on CPU [^33]
    - Frame size: 512 samples = 32ms at 16kHz [^12]

Ref: snakers4/silero-vad. (2024). GitHub: https://github.com/snakers4/silero-vad
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import onnxruntime as ort


# Silero VAD ONNX model — v4.0 (latest stable)
SILERO_ONNX_URL = (
    "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx"
)

# Audio parameters
SAMPLE_RATE = 16000          # Silero VAD expects 16kHz [^10]
FRAME_SIZE = 512             # 512 samples = 32ms at 16kHz [^12]
HIDDEN_SIZE = 128            # LSTM hidden state size
CELL_SIZE = 128              # LSTM cell state size

# Dual-threshold hysteresis [^12]
THRESHOLD_SPEECH = 0.50      # Start speech when prob > 0.5
THRESHOLD_SILENCE = 0.35     # End speech when prob < 0.35

# Timing (in frames)
MIN_SPEECH_FRAMES = 15       # ~480ms min utterance
MIN_SILENCE_FRAMES = 25      # ~800ms silence hangover for conversational


def _get_model_path() -> Path:
    """Return cached path to Silero ONNX model; download if missing."""
    cache_dir = Path(__file__).parent.parent.parent / "models"
    cache_dir.mkdir(exist_ok=True)
    model_path = cache_dir / "silero_vad.onnx"

    if not model_path.exists():
        print(f"[SileroVAD] Downloading model to {model_path} ...")
        urllib.request.urlretrieve(SILERO_ONNX_URL, model_path)
        print("[SileroVAD] Download complete.")

    return model_path


class SileroVAD:
    """
    Neural VAD using Silero's ONNX model.

    Usage:
        vad = SileroVAD()
        for pcm_chunk in audio_stream:
            is_speech, is_end = vad.process(pcm_chunk)
            if is_end:
                # Utterance complete
    """

    def __init__(
        self,
        threshold_speech: float = THRESHOLD_SPEECH,
        threshold_silence: float = THRESHOLD_SILENCE,
        min_speech_frames: int = MIN_SPEECH_FRAMES,
        min_silence_frames: int = MIN_SILENCE_FRAMES,
        model_path: Optional[str] = None,
    ):
        self.threshold_speech = threshold_speech
        self.threshold_silence = threshold_silence
        self.min_speech_frames = min_speech_frames
        self.min_silence_frames = min_silence_frames

        # ONNX session
        path = model_path or str(_get_model_path())
        self._session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])

        # LSTM state (must persist across frames)
        self._hidden = np.zeros((2, 1, HIDDEN_SIZE), dtype=np.float32)
        self._cell = np.zeros((2, 1, CELL_SIZE), dtype=np.float32)

        # Tracking
        self._speech_prob: float = 0.0
        self._speech_frames: int = 0
        self._silence_frames: int = 0
        self._in_speech: bool = False
        self._total_frames: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, pcm_int16: bytes) -> Tuple[bool, bool]:
        """
        Process a chunk of 16kHz PCM int16 audio.

        Returns:
            (is_currently_speech, is_utterance_end)
            - is_currently_speech: True if speech is detected in this frame
            - is_utterance_end: True if the utterance just ended
        """
        # Convert int16 bytes → float32 normalized [-1, 1]
        samples = np.frombuffer(pcm_int16, dtype=np.int16).astype(np.float32) / 32768.0

        is_end = False
        # Process in FRAME_SIZE windows with stride = FRAME_SIZE (no overlap for speed)
        for i in range(0, len(samples), FRAME_SIZE):
            frame = samples[i : i + FRAME_SIZE]
            if len(frame) < FRAME_SIZE:
                # Pad last frame
                frame = np.pad(frame, (0, FRAME_SIZE - len(frame)))

            prob = self._infer(frame)
            self._speech_prob = prob
            self._total_frames += 1

            if self._in_speech:
                self._speech_frames += 1
                if prob < self.threshold_silence:
                    self._silence_frames += 1
                    if self._silence_frames >= self.min_silence_frames:
                        # Utterance ended
                        is_end = True
                        self._in_speech = False
                        self._speech_frames = 0
                        self._silence_frames = 0
                else:
                    self._silence_frames = 0
            else:
                if prob > self.threshold_speech:
                    self._in_speech = True
                    self._speech_frames = 1
                    self._silence_frames = 0

        return self._in_speech, is_end

    def reset(self) -> None:
        """Reset LSTM state and tracking counters for a new utterance."""
        self._hidden = np.zeros((2, 1, HIDDEN_SIZE), dtype=np.float32)
        self._cell = np.zeros((2, 1, CELL_SIZE), dtype=np.float32)
        self._speech_prob = 0.0
        self._speech_frames = 0
        self._silence_frames = 0
        self._in_speech = False
        self._total_frames = 0

    @property
    def speech_probability(self) -> float:
        """Latest speech probability (0.0–1.0)."""
        return self._speech_prob

    @property
    def is_speaking(self) -> bool:
        """True if currently in speech state."""
        return self._in_speech

    # ------------------------------------------------------------------
    # ONNX inference
    # ------------------------------------------------------------------

    def _infer(self, frame: np.ndarray) -> float:
        """Run ONNX inference on a single frame. Returns speech probability."""
        input_tensor = frame.reshape(1, -1).astype(np.float32)
        outputs = self._session.run(
            None,
            {
                "input": input_tensor,
                "h": self._hidden,
                "c": self._cell,
                "sr": np.array([SAMPLE_RATE], dtype=np.int64),
            },
        )
        prob = float(outputs[0].item())
        self._hidden = outputs[1]
        self._cell = outputs[2]
        return prob


# References
# [^10]: arXiv (2026). Real-Time Voicemail Detection in Telephony Audio. arXiv:2604.09675v1.
# [^12]: vexyl AI Voice Gateway. (2025). Silero VAD configuration.
# [^33]: Silero Team. (2024). Silero VAD: Pre-trained enterprise-grade VAD.
