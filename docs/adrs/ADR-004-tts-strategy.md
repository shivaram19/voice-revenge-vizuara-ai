# ADR-004: TTS Engine Strategy

## Status
**Accepted** — 2026-04-25

## Context
TTS is the final stage of the voice pipeline. Choice affects latency, quality, cost, and deployment flexibility. Candidates: Piper (edge), Coqui VITS/XTTS (cloud), ElevenLabs (commercial API).

## Decision
**Use Piper TTS as default for all self-hosted deployments. Use Coqui XTTS v2 for voice-cloning scenarios. Use ElevenLabs Flash only as enterprise fallback.**

## Rationale

### Piper TTS
- **Latency**: RTF ~0.1× on x86 CPU; TTFB <100ms.
- **Cost**: Zero per-minute cost; no GPU required.
- **Quality**: MOS ~3.5 (good enough for informational agents) [^48].
- **Deployment**: ONNX Runtime; runs on Raspberry Pi 4, server, or edge device.
- **Privacy**: Fully local; audio never leaves infrastructure.

### Coqui XTTS v2
- **Latency**: RTF ~0.2× on GPU; requires GPU for real-time.
- **Quality**: MOS ~4.2; voice cloning from 6-second sample [^51].
- **Cost**: GPU hour cost; open-source weights.
- **Risk**: Original company dissolved; community-maintained.

### ElevenLabs Flash
- **Latency**: TTFB ~220ms [^19].
- **Quality**: Excellent (MOS > 4.5).
- **Cost**: $0.18/1K characters; scales linearly with usage.
- **Use**: Fallback for premium enterprise tier only.

## Tiered Strategy

| Tier | Users | TTS Engine | Justification |
|------|-------|-----------|---------------|
| Free / Edge | 80% | Piper CPU | Cost-zero; privacy-first |
| Pro | 18% | Coqui VITS GPU | Better prosody; multilingual |
| Enterprise | 2% | ElevenLabs Flash | Maximum naturalness; API fallback |

## Consequences

### Positive
- 80% of traffic requires zero GPU time for TTS.
- Edge deployments (hospitals, factories) can run fully offline.
- Open-source stack avoids vendor lock-in.

### Negative
- Piper voices are less expressive than neural cloud APIs.
- XTTS v2 community support is uncertain long-term.
- Voice cloning requires GPU; cannot run on edge.

## Research Provenance
- Hansen (2023): Piper achieves "real-time synthesis on Raspberry Pi 4" [^48].
- Keith et al. (2024): Piper (7M params) evaluated alongside Nix-TTS and Mini-VITS [^51].
- Chanl.ai (2026): ElevenLabs Flash TTFB measured at 219-236ms [^19].

## Revisit Trigger
Revisit if:
1. Orpheus TTS (LLM-based) achieves <100ms TTFB with vLLM serving.
2. Piper adds voice cloning or emotional prosody control.
3. ElevenLabs reduces pricing by >50%.

## References
[^19]: Chanl.ai. (2026). Voice Agent Platform Architecture.
[^48]: Hansen, M. (2023). Piper. *GitHub: rhasspy/piper*.
[^51]: Keith et al. (2024). Text-to-speech on Edge Devices. *SIGUL*.

[^1]: Hansen, M. (2023). Piper. *GitHub: rhasspy/piper*.
[^2]: Keith et al. (2024). Text-to-speech on Edge Devices. *SIGUL*.
[^3]: Chanl.ai. (2026). Voice Agent Platform Architecture.
