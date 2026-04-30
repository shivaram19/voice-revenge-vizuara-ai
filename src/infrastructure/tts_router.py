"""
TTSRouter — Plug-and-Play Routing Across TTS Adapters
======================================================
Routes a synthesise call to the appropriate TTS provider based on the
parent's language preference. Conforms to the same single-method
`synthesize(text, model=None, ssml=False) -> bytes` shape every adapter
exposes, so the rest of the pipeline does not need to know which
provider is serving any given turn.

ADR-019 establishes this layer. The route table is constructed once at
the composition root (`lifespan.py`) from environment-driven keys; if a
provider is unavailable (no API key, vendor down), the router falls
back to the default — typically Deepgram Aura for English content. This
preserves the uniform-voice policy from commit `3254a5a` per call (one
provider per call, not mid-utterance), while letting *different calls*
use different providers based on the parent.

The router DOES NOT:
    - inspect the text content to guess language
    - mix two providers within one turn
    - cache audio across calls
    - introspect adapters via duck typing

It DOES:
    - accept a `lang_pref` hint (case-insensitive) and look it up in
      a configured route table
    - delegate to the default adapter when no route matches or the
      route's adapter is None (vendor not configured)
    - propagate vendor errors verbatim (let pipeline observe + retry
      via existing telemetry)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class _SynthesizeAdapter(Protocol):
    """Structural shape every TTS adapter must satisfy."""

    def synthesize(
        self,
        text: str,
        model: Optional[str] = None,
        ssml: bool = False,
    ) -> bytes:
        ...


class TTSRouter:
    """
    Per-call TTS provider selection.

    Args:
        default: The TTS adapter used when no route matches. In the
            current deployment this is `DeepgramTTSClient` for English
            content.
        by_language: Optional map from lower-cased language preference
            (e.g. "telugu") to a TTS adapter that should serve that
            preference. Keys are matched case-insensitively. Values may
            be `None` to express "this language has been considered but
            no adapter is configured" (composition root used to honour
            the fall-through to default in that case).
    """

    def __init__(
        self,
        default: _SynthesizeAdapter,
        by_language: Optional[Dict[str, Optional[_SynthesizeAdapter]]] = None,
    ) -> None:
        self.default = default
        self._routes: Dict[str, _SynthesizeAdapter] = {}
        for k, v in (by_language or {}).items():
            if v is not None:
                self._routes[k.strip().lower()] = v

    def has_route(self, lang_pref: str) -> bool:
        """True if a non-default adapter is configured for `lang_pref`."""
        return (lang_pref or "").strip().lower() in self._routes

    def synthesize(
        self,
        text: str,
        model: Optional[str] = None,
        ssml: bool = False,
        lang_pref: str = "",
        pace: Optional[float] = None,
    ) -> bytes:
        """
        Route the synthesise call. The `lang_pref` kwarg is the
        addition over the per-adapter contract. `pace` is a per-call
        override forwarded only to adapters that accept it (Sarvam
        Bulbul); plain adapters like Deepgram ignore it.
        """
        provider = self._routes.get((lang_pref or "").strip().lower())
        if provider is None:
            return self.default.synthesize(text, model=model, ssml=ssml)
        # Inspect provider signature: only Sarvam currently accepts pace.
        try:
            return provider.synthesize(text, model=model, ssml=ssml, pace=pace)
        except TypeError:
            # Provider doesn't accept pace; fall back to standard call.
            return provider.synthesize(text, model=model, ssml=ssml)

    def routes_summary(self) -> Dict[str, str]:
        """For observability / logs at lifespan startup."""
        return {
            "default": type(self.default).__name__,
            "by_language": {
                k: type(v).__name__ for k, v in self._routes.items()
            },
        }


__all__ = ["TTSRouter"]
