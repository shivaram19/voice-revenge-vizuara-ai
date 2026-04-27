# DFS-01: Whisper Ecosystem — Depth-First Analysis

**Research Phase**: DFS traversal from ASR node  
**Scope**: Whisper, faster-whisper, Distil-Whisper, whisper.cpp  
**Date**: 2026-04-25

---

## Node Hierarchy

```
ASR (root)
└── Whisper Family
    ├── OpenAI Whisper (original)
    ├── faster-whisper (CTranslate2 optimization)
    ├── Distil-Whisper (knowledge distillation)
    └── whisper.cpp (edge/portable C++ port)
```

---

## 1. OpenAI Whisper (Original)

### Architecture
**Type**: Transformer encoder-decoder (Seq2Seq)  
**Input**: Log-mel spectrogram (30-second windows)  
**Output**: Text tokens (autoregressive decoding)  
**Parameters**: 39M (tiny) → 1.55B (large-v3)  
**Training data**: 680,000 hours of weakly supervised multilingual audio [^1].

### Key Technical Properties
1. **Fixed-length encoding**: Processes 30-second chunks regardless of actual speech duration. Shorter audio is zero-padded. This creates a **constant computational floor** — the encoder cost is the same for 1s and 30s of audio [^76].
2. **Multitask conditioning**: Special tokens specify language, task (transcribe/translate), and timestamp prediction. This unified design eliminates the need for separate models per task [^1].
3. **Text normalizer**: Custom normalization before WER computation. This improves reported WER but does not reflect real-world scenarios where training data contains mismatched labels (e.g., silent audio labeled with full sentences) [^77].

### Performance Benchmarks
| Model | Params | LibriSpeech clean WER | TED-LIUM WER |
|-------|--------|----------------------|--------------|
| tiny | 39M | ~8.0% | — |
| base | 74M | ~5.5% | — |
| small | 244M | ~3.5% | — |
| medium | 769M | ~3.0% | — |
| large-v2 | 1.55B | ~2.7% | 4.7% |
| large-v3 | 1.55B | ~2.5% | — |

**Citation**: Radford et al. (2022), Table 8 [^1].

### Critical Limitation for Real-Time
The 30-second fixed window creates a **latency floor**. Even the `tiny.en` model has a firm lower bound of ~500ms on ARM processors because the encoder must process the full 30-second spectrogram [^76]. This makes vanilla Whisper unsuitable for real-time streaming without modification.

---

## 2. faster-whisper

### Optimization Strategy
**Mechanism**: Reimplementation using CTranslate2, a fast inference engine for Transformer models.
- **Weight quantization**: INT8 quantization reduces memory bandwidth.
- **Optimized kernels**: Custom CUDA kernels for attention and feed-forward layers.
- **Batch decoding**: Efficient batched beam search.

### Measured Speedup
**Claim**: Up to 4× faster than original Whisper with equivalent accuracy [^5].

**Independent verification** (APSIPA 2025):
| Model | Avg WER | Avg RTF | Avg Latency |
|-------|---------|---------|-------------|
| Medium | 9.0% | 0.78 | 9.6s |
| Large | 8.5% | 1.18 | 12.7s |
| Large-V2 | 8.3% | 1.16 | 11.5s |
| Distil-Large-V2 | 7.1% | 0.68 | 8.6s |

*Note: These latencies reflect speaker recognition integration overhead, not pure ASR.*

**Citation**: SYSTRAN (2023), faster-whisper GitHub; APSIPA 2025 paper [^5][^73].

---

## 3. Distil-Whisper

### Architecture
**Type**: Knowledge-distilled Whisper (encoder-decoder)  
**Parameters**: 756M (49% smaller than large-v2)  
**Decoder layers**: Reduced from 32 to 2  
**Training method**: Pseudo-labelling with WER threshold filter on 21,170 hours of public audio [^77].

### Performance Claims vs Evidence
| Metric | Claim | Evidence Quality |
|--------|-------|------------------|
| Speedup | 5.8× faster | T1 (peer-reviewed paper) |
| WER delta | Within 1% on OOD short-form | T1 |
| Hallucination reduction | 1.3× fewer repetitions | T1 |
| Long-form performance | Outperforms Whisper | T1 (chunked algorithm is 9× faster) |

### Speculative Decoding Synergy
Distil-Whisper can be paired with original Whisper as an **assistant model** for speculative decoding [^24]:
- Distil-Whisper generates draft tokens quickly.
- Whisper large-v2 verifies drafts.
- Result: 2× speedup with **identical outputs** to original model.
- Cost: Only 8% parameter increase over base Whisper.

**Citation**: Leviathan et al. (2023), "Fast Inference from Transformers via Speculative Decoding" [^24].

### Interpretation (Engine Perception)
Distil-Whisper is the **Pareto-optimal point** in the quality-speed trade-off for English ASR. It is not merely "faster Whisper" — it is a different architectural choice (smaller decoder) that happens to generalize better due to reduced hallucination. For non-English, the original Whisper or fine-tuned variants remain superior.

---

## 4. whisper.cpp

### Purpose
C/C++ port of Whisper for **on-device, offline-first** deployment. No PyTorch dependency. Runs on CPU, GPU (via OpenCL/Metal/CUDA), and embedded devices [^5].

### Use Cases
- **Privacy**: Audio never leaves device.
- **Edge**: Raspberry Pi, mobile phones, browsers (via WASM).
- **Cost**: Zero per-minute API cost.

### Trade-offs
| Dimension | whisper.cpp | Cloud Whisper |
|-----------|-------------|---------------|
| Latency | Higher (CPU-bound) | Lower (GPU) |
| Accuracy | Equivalent (same weights) | Equivalent |
| Power | Battery drain on mobile | Server power |
| Model size | Must fit on device | Unlimited |

---

## Comparative Decision Matrix

| Use Case | Recommendation | Rationale |
|----------|---------------|-----------|
| Real-time streaming (English) | **Distil-Whisper** | Best speed/quality trade-off |
| Real-time streaming (multilingual) | **faster-whisper large-v3** | Language coverage + optimization |
| On-device / privacy-critical | **whisper.cpp** | No network, no cloud cost |
| Batch transcription (quality-first) | **Whisper large-v3** | Lowest WER |
| Research / experimentation | **Whisper + HF Transformers** | Maximum flexibility |

---

## References

[^1]: Radford, A., et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision. *arXiv:2212.04356*.
[^76]: arXiv:2410.15608. Speech Recognition for Live Transcription and Voice Commands.
[^77]: arXiv:2501.00425. Whisper Turns Stronger: Augmenting Wav2Vec 2.0 for Superior ASR.
[^5]: SYSTRAN. (2023). faster-whisper. *GitHub: SYSTRAN/faster-whisper*.
[^73]: APSIPA 2025. Integrating Faster Whisper with Deep Learning Speaker Recognition.
[^3]: Gandhi, S., et al. (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. *arXiv:2311.00430*.
[^24]: Leviathan, Y., Kalman, M., & Matias, Y. (2023). Fast Inference from Transformers via Speculative Decoding. *ICML*.
[^4]: Gerganov, G. (2023). whisper.cpp. *GitHub: ggerganov/whisper.cpp*.
