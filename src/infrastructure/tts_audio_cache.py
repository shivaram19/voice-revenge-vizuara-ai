"""
TTS Audio Cache — Region-Scoped Persistent Disk Storage
========================================================
Eliminates redundant TTS API calls by caching synthesized audio on disk,
scoped by REGION so Suryapet pronunciations never leak into Coastal
Andhra calls.

Key = hash(region_tag + text + speaker + pace + temperature + lang).
Value = WAV bytes.

Why region-scoped:
- "Namaste" in Suryapet cache → "Namaskaaram"
- "Namaste" in Coastal Andhra cache → "Namaste" (standard)
- Same text, different pronunciation → different cache entries

Storage:
- Local dev: ./tts_cache/{region_tag}/
- Container: /app/cache/tts/{region_tag}/

Ref: User directive 2026-05-02 (dialect labeling and caching).
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Optional


def _cache_key(
    text: str,
    speaker: str,
    pace: float,
    temperature: float,
    lang: str,
) -> str:
    """Deterministic cache key."""
    payload = f"{text}|{speaker}|{pace:.3f}|{temperature:.3f}|{lang}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _cache_path(key: str, region_tag: str, cache_dir: Path) -> Path:
    return cache_dir / region_tag / key[:2] / f"{key}.wav"


class TTSAudioCache:
    """
    Disk-backed audio cache scoped by region_tag.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        max_age_days: int = 30,
    ) -> None:
        self.cache_dir = Path(cache_dir or os.getenv("TTS_CACHE_DIR", "./tts_cache"))
        self.max_age_days = max_age_days
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(
        self,
        text: str,
        speaker: str,
        pace: float,
        temperature: float,
        lang: str,
        region_tag: str = "default",
    ) -> Optional[bytes]:
        """Return cached WAV bytes, or None if not found / expired."""
        key = _cache_key(text, speaker, pace, temperature, lang)
        path = _cache_path(key, region_tag, self.cache_dir)

        if not path.exists():
            return None

        age_days = (time.time() - path.stat().st_mtime) / 86400
        if age_days > self.max_age_days:
            path.unlink(missing_ok=True)
            return None

        return path.read_bytes()

    def put(
        self,
        text: str,
        speaker: str,
        pace: float,
        temperature: float,
        lang: str,
        audio: bytes,
        region_tag: str = "default",
    ) -> None:
        """Store WAV bytes to disk cache."""
        key = _cache_key(text, speaker, pace, temperature, lang)
        path = _cache_path(key, region_tag, self.cache_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(audio)
        tmp.rename(path)

    def stats(self, region_tag: Optional[str] = None) -> dict:
        """Return cache size and file count, optionally scoped to region."""
        if region_tag:
            base = self.cache_dir / region_tag
        else:
            base = self.cache_dir
        files = list(base.rglob("*.wav")) if base.exists() else []
        total_bytes = sum(f.stat().st_size for f in files)
        return {
            "file_count": len(files),
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir),
            "region_tag": region_tag or "all",
        }


_default_cache: Optional[TTSAudioCache] = None


def get_cache() -> TTSAudioCache:
    global _default_cache
    if _default_cache is None:
        _default_cache = TTSAudioCache()
    return _default_cache


__all__ = ["TTSAudioCache", "get_cache"]
