# ADR-023: Self-Hosted Real-Time ASR with Moonshine v2

**Date:** 2026-05-02  
**Status:** Approved  
**Scope:** Choose the self-hosted English ASR model for the WebRTC browser-client transcription path  
**Risk Level:** Medium

---

## Context

The voice-agent platform currently relies on Deepgram for streaming STT. For a self-hosted, WebRTC-based browser demo and potential cost-sensitive deployments, we need an on-premise English ASR model that supports:

1. Native streaming inference (sub-200 ms first-word latency).
2. Small enough footprint to run on a single GPU or CPU container.
3. Apache 2.0 or similarly permissive license.
4. Competitive WER on conversational English, including Indian-accented speech.

Candidates evaluated:

| Model | Params | Streaming | WER (LS) | Latency (Linux) | License |
|---|---|---|---|---|---|
| OpenAI Whisper large-v3 | 1550M | No (fixed 30s window) | 2.1% | ~1-2s | MIT |
| faster-whisper distil-large-v3 | 756M | Chunked only | ~3.3% | 200-500ms | MIT |
| NVIDIA Parakeet TDT 1.1B | 1100M | Yes | 6.85% | ~150ms | CC BY 4.0 |
| Canary-Qwen 1.6B | 1600M | Yes | 6.14% | ~200ms | CC BY-NC 4.0 |
| Moonshine v2 Medium Streaming | 245M | Native | 6.65% | 269ms | Apache 2.0 |

## Decision

Adopt **Moonshine v2 Medium Streaming** as the self-hosted ASR for the WebRTC path.

Rationale:
- Native streaming encoder avoids Whisper's 30-second window buffering, cutting perceived latency [^Moonshine2026].
- 245M parameters yield a ~270 MB quantized ONNX footprint, deployable on L4 GPU or modern CPU.
- Apache 2.0 license avoids the non-commercial restriction of Canary-Qwen and attribution complexity of Parakeet.
- Empirical smoke test on a Suryapet/Telangana-English call recording transcribed 84.7s of audio in 9.3s on CPU, confirming real-time feasibility.

## Consequences

### Positive
- Removes per-minute STT vendor cost for browser-demo and low-cost deployments.
- Single-model stack simplifies operations compared to a dual Deepgram + self-hosted setup.
- Moonshine's built-in streaming VAD reduces the need for a separate Silero VAD in the hot path.

### Negative
- Indian-accented English WER has not yet been benchmarked; accuracy may trail Deepgram's Nova-2 on code-mixed Telugu/English.
- Moonshine is English-only in the medium-streaming variant; multilingual calls still require Deepgram.
- ONNX Runtime CUDA execution must be validated in the target container (CUDA 12.1).

### Risks
- Model accuracy degradation on noisy browser microphone audio.
- Dependency on a relatively new model family (<1 year old); ecosystem maturity behind Whisper.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|---|---|---|---|
| Whisper Turbo (faster-whisper) | Best accuracy, mature tooling | Fixed-window latency, larger model | Fails native streaming requirement |
| Parakeet TDT 1.1B | SOTA streaming WER | 1.1B params, CC BY license | Larger footprint; license less permissive |
| Canary-Qwen 1.6B | Lowest WER in table | Non-commercial license | License incompatible with product use |
| Deepgram Nova-2 (status quo) | Excellent accuracy, no infra | Vendor cost, data residency concerns | Not self-hosted |

## References

- [^Moonshine2026]: King, E., et al. (2026). Moonshine v2: Ergodic Streaming Encoder ASR for Latency-Critical Speech Applications. *arXiv:2602.12241*.
- [^MoonshineDocs]: Moonshine Voice documentation, model benchmarks, 2026. https://moonshine.ai
- [^Whisper2022]: Radford, A., et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision. *arXiv:2212.04356*.

## Metrics

- `moonshine_transcription_latency_ms` — histogram of `last_transcription_latency_ms` per final event
- `moonshine_rtf` — real-time factor for offline transcription path
- `webrtc_audio_frames_received_total` — counter of RTP frames ingested
- Target: WER <15% on a held-out Indian-English call test set before production use
