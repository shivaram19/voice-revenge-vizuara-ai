"""
Demo Model Downloader
=====================
Downloads the lightweight models needed for the live AI pipeline demo:

    - faster-whisper "tiny" (~150 MB): CPU-friendly ASR with <2s latency
      on consumer hardware [^3][^5].
    - Piper "en_US-lessac-medium" (~60 MB): Neural TTS at 22.05 kHz,
      real-time factor ~0.3 on CPU [^9].

Usage:
    python scripts/setup-demo-models.py

Research Provenance:
    - Distil-Whisper achieves 5.8× speedup over Whisper with <1% WER loss [^3].
    - faster-whisper (CTranslate2) provides additional 4× speedup [^5].
    - Piper TTS runs at real-time factor <1.0 on Raspberry Pi 4 [^9].
    - For demo purposes, the "tiny" STT model trades absolute accuracy
      for sub-second transcription latency [^1].
"""

from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv

_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    load_dotenv(dotenv_path=str(_env))

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MODELS_DIR = PROJECT_ROOT / "models"
PIPER_DIR = MODELS_DIR / "piper"


def setup_faster_whisper() -> None:
    """Trigger faster-whisper model download by loading it."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[ERROR] faster-whisper not installed. Run: pip install faster-whisper")
        sys.exit(1)

    print("Downloading faster-whisper 'tiny' model (~150 MB)...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print("[OK] faster-whisper 'tiny' ready.")


def setup_piper() -> None:
    """Download Piper voice model if not present."""
    PIPER_DIR.mkdir(parents=True, exist_ok=True)
    model_path = PIPER_DIR / "en_US-lessac-medium.onnx"
    json_path = PIPER_DIR / "en_US-lessac-medium.onnx.json"

    if model_path.exists() and json_path.exists():
        print("[OK] Piper voice model already present.")
        return

    print("Downloading Piper 'en_US-lessac-medium' voice (~60 MB)...")
    import urllib.request

    base_url = (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
        "en/en_US/lessac/medium/"
    )
    for filename in [json_path.name, model_path.name]:
        url = base_url + filename
        dest = PIPER_DIR / filename
        print(f"  {filename} ...")
        urllib.request.urlretrieve(url, dest)

    print("[OK] Piper voice model ready.")


def main() -> int:
    print("=" * 60)
    print("DEMO MODEL SETUP")
    print("=" * 60)
    setup_faster_whisper()
    setup_piper()
    print("\nAll models downloaded. You can now run the live AI demo.")
    return 0


# References
# [^1]: Radford, A., et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision. arXiv:2212.04356.
# [^3]: Gandhi, S., et al. (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. arXiv:2311.00430.
# [^5]: SYSTRAN. (2023). faster-whisper. GitHub: SYSTRAN/faster-whisper.
# [^9]: Hansen, M. (2023). Piper: A fast, local neural text-to-speech system. GitHub: rhasspy/piper.

if __name__ == "__main__":
    sys.exit(main())
