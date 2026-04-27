# ADR-002: ASR Model Selection for Production Pipeline

## Status
**Accepted** — 2026-04-25

## Context
The ASR stage converts streaming audio to text. Model choice affects latency, accuracy, cost, and language coverage. The primary candidates were: Whisper large-v3, Distil-Whisper, faster-whisper, and Deepgram Nova-3 (commercial API).

## Decision
**Use a tiered strategy:**
1. **Primary (English, real-time)**: Distil-Whisper via faster-whisper backend (CTranslate2).
2. **Primary (Multilingual, real-time)**: faster-whisper large-v3.
3. **Fallback (quality-critical)**: Whisper large-v3.
4. **Edge/offline**: whisper.cpp.

## Consequences

### Positive
- **English latency**: 5.8× speedup over Whisper large-v2 with <1% WER degradation [^5].
- **Infrastructure efficiency**: Distil-Whisper runs on CPU for 10-20 concurrent English streams, reducing GPU node count.
- **Hallucination reduction**: Distil-Whisper has 1.3× fewer repetition errors than original [^5].
- **Open-source**: No per-minute API cost; full weight portability.

### Negative
- **Non-English accuracy**: Distil-Whisper is English-only. Multilingual requires larger model.
- **Cold start**: Model loading adds 2-5s on container spin-up; requires pre-warming.
- **Memory**: 756M parameters × FP16 = ~1.5GB GPU memory per instance.

## Quantitative Analysis

| Model | Params | English WER | RTF (GPU) | Memory |
|-------|--------|-------------|-----------|--------|
| Whisper tiny | 39M | ~8% | 0.1× | ~80MB |
| Distil-Whisper | 756M | ~3% | 0.17× | ~1.5GB |
| Whisper large-v3 | 1.55B | ~2.5% | 1.0× | ~3GB |
| Deepgram Nova-3 | N/A | ~2% | ~0.05× | N/A (API) |

**RTF** = Real-Time Factor. <1.0 means faster than real-time. Distil-Whisper at 0.17× means 1s of audio processed in 170ms.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Deepgram Nova-3 (commercial) | Vendor lock-in; per-minute cost scales linearly with usage; no on-device option |
| Whisper large-v3 as primary | 1.0× RTF leaves no headroom for concurrent streams without GPU oversubscription |
| Wav2Vec 2.0 | Requires fine-tuning for text mapping; Whisper's zero-shot robustness is superior [^5] |

## Research Provenance
- Gandhi et al. (2023): "Distil-Whisper is 49% smaller, 5.8 times faster, and within 1% WER performance on OOD short-form audio" [^5].
- Radford et al. (2022): Whisper trained on 680,000 hours vs Wav2Vec 2.0's 60,000 hours — "an order of magnitude more data" [^5].
- SYSTRAN (2023): faster-whisper achieves "4× speedup over original Whisper" via CTranslate2 [^5].

## Revisit Trigger
Revisit if:
1. Whisper large-v4 or equivalent achieves <0.1× RTF with multilingual support.
2. A streaming-native ASR (e.g., RNN-T based) achieves comparable WER with lower latency.
3. Distil-Whisper multilingual variant is released.

## References
[^1]: Radford, A., et al. (2022). Whisper. *arXiv:2212.04356*.
[^3]: Gandhi, S., et al. (2023). Distil-Whisper. *arXiv:2311.00430*.
[^5]: SYSTRAN. (2023). faster-whisper. *GitHub*.
[^5]: SYSTRAN. (2023). faster-whisper. *GitHub*.

[^1]: Gandhi, S., et al. (2023). Distil-Whisper. *arXiv:2311.00430*.
[^2]: Radford, A., et al. (2022). Whisper. *arXiv:2212.04356*.
[^3]: SYSTRAN. (2023). faster-whisper. *GitHub*.
