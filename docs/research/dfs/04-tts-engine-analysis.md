# DFS-04: TTS Engine Analysis — Piper, Coqui, and the Edge-Cloud Spectrum

**Research Phase**: DFS traversal from TTS node  
**Scope**: Open-source TTS engines, latency, quality, deployment targets  
**Date**: 2026-04-25

---

## Quality Metrics

| Metric | Definition | Measurement |
|--------|-----------|-------------|
| **MOS** | Mean Opinion Score (1-5) | Human listeners rate naturalness |
| **CMOS** | Comparative MOS | Side-by-side preference vs reference |
| **RTF** | Real-Time Factor | Time to synthesize 1s of audio |
| **PER** | Phoneme Error Rate | Deviation from target pronunciation |

---

## Engine Comparison

### Piper TTS
**Developer**: Michael Hansen (Rhasspy project)  
**Architecture**: VITS-based, distilled to ~7-15M parameters  
**Runtime**: ONNX Runtime (CPU-optimized)  
**Deployment**: Raspberry Pi 4, x86 server, browser (WASM)

**Performance**:
| Model | Params | RTF (RPi 4) | RTF (x86) | Quality |
|-------|--------|-------------|-----------|---------|
| en_US-lessac | ~15M | ~0.5× | ~0.1× | Good |
| en_US-ryan | ~15M | ~0.5× | ~0.1× | Good |
| en_GB-northern_english_male | ~15M | ~0.5× | ~0.1× | Good |

**Pros**:
- Fastest open-source TTS for CPU.
- No GPU required.
- Privacy: fully local.
- Simple HTTP API.

**Cons**:
- Limited language coverage (~20 languages).
- No voice cloning.
- Prosody less expressive than neural cloud APIs.

**Citation**: Hansen (2023) [^48]; SIGUL 2024 evaluation [^51].

---

### Coqui TTS
**Status**: Community-maintained (original company dissolved late 2024)  
**Architecture**: Modular toolkit — Tacotron2, FastSpeech2, VITS, YourTTS, XTTS  
**Runtime**: PyTorch

**Performance**:
| Model | Params | RTF (GPU) | Quality | Notes |
|-------|--------|-----------|---------|-------|
| VITS | ~29M | ~0.05× | Very Good | End-to-end |
| XTTS v2 | ~400M | ~0.2× | Excellent | Voice cloning |
| YourTTS | ~30M | ~0.1× | Good | Multi-speaker |

**Pros**:
- Most comprehensive open-source TTS toolkit.
- Voice cloning (XTTS v2).
- Many languages.

**Cons**:
- Requires PyTorch → heavy dependency.
- XTTS v2 needs GPU for real-time.
- Community future uncertain.

**Citation**: Coqui AI GitHub [^10]; tderflinger.com review [^73].

---

### Nix-TTS (Research Baseline)
**Architecture**: VITS distillation  
**Parameters**: 5.23M  
**RTF**: 1.97 (Raspberry Pi 3B) vs VITS 16.50 [^11]  
**CMOS**: -0.27 vs VITS (MOS 4.43) [^11]

**Significance**: Demonstrates that sub-6M parameter models can achieve near-VITS quality. Piper builds on this lineage.

---

### Cloud TTS (Reference Baseline)
| Provider | TTFB | Quality | Cost |
|----------|------|---------|------|
| ElevenLabs turbo v2.5 | ~220ms | Excellent | $0.18/1K chars |
| OpenAI TTS | ~300ms | Very Good | $0.015/1K chars |
| Google Cloud TTS | ~200ms | Good | $4/1M chars |

---

## Decision Matrix

| Deployment | Recommendation | Model |
|------------|---------------|-------|
| Edge / IoT | **Piper** | en_US-lessac |
| On-prem server (cost-sensitive) | **Piper** or **Coqui VITS** | — |
| On-prem server (quality-sensitive) | **Coqui XTTS v2** | — |
| Cloud (latency-critical) | **ElevenLabs Flash** | eleven_turbo_v2_5 |
| Cloud (cost-sensitive) | **OpenAI TTS** | tts-1-hd |

---

## Streaming TTS Architecture

Not all TTS engines support streaming. For those that don't, use **sentence-level chunking**:

```
LLM Token Stream
     │
     ▼
Sentence Buffer (accumulate until .!?)
     │
     ▼
TTS Synthesize(sentence)
     │
     ▼
Audio Chunk Stream ──► Client
```

**Buffer Rules**:
1. Detect sentence-ending punctuation.
2. Exclude abbreviations (Dr., Mr., PM.).
3. Minimum length: 10 characters.
4. Flush remainder on LLM stream end.

**Citation**: Pipecat SentenceAggregator; SigArch (2026) [^16].

---

## References
[^10]: Coqui AI. (2023). Coqui TTS. *GitHub*.
[^11]: Chevi et al. (2023). Nix-TTS. *Edge GenAI preprint*.
[^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents. *arXiv:2603.05413*.
[^48]: Hansen, M. (2023). Piper. *GitHub: rhasspy/piper*.
[^51]: Keith et al. (2024). Text-to-speech on Edge Devices. *SIGUL*.
[^73]: tderflinger.com. (2024). Open Source Voice Bot ASR/TTS Guide.

[^1]: Hansen, M. (2023). Piper. *GitHub: rhasspy/piper*.
[^2]: Keith et al. (2024). Text-to-speech on Edge Devices. *SIGUL*.
[^3]: Coqui AI. (2023). Coqui TTS. *GitHub*.
[^4]: tderflinger.com. (2024). Open Source Voice Bot ASR/TTS Guide.
[^5]: Chevi et al. (2023). Nix-TTS. *Edge GenAI preprint*.
[^6]: SigArch. (2026). Building Enterprise Realtime Voice Agents. *arXiv:2603.05413*.
