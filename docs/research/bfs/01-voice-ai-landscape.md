# BFS-01: Voice AI Landscape — Breadth-First Mapping

**Research Phase**: BFS Level 0 — Root Node Expansion  
**Scope**: Full curriculum domain coverage  
**Date**: 2026-04-25

---

## Executive Summary

The voice AI landscape is not a linear pipeline but a **heterogeneous graph** of interacting subsystems. This document maps all 8 curriculum modules as nodes in a dependency graph, establishing which domains are prerequisites for which others.

---

## Domain Dependency Graph

```
                    ┌─────────────────┐
                    │  Module 1       │
                    │  Voice Agent    │
                    │  Architecture   │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │ Module 2    │   │ Module 3    │   │ Module 4    │
    │ ASR         │   │ TTS         │   │ LLM Brain   │
    │ Foundations │   │ & Output    │   │ & Reasoning │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Module 5       │
                    │  Tool Use,      │
                    │  Memory, Agent  │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │ Module 6    │   │ Module 7    │   │ Module 8    │
    │ Real-Time   │   │ Production  │   │ Final       │
    │ Streaming   │   │ Architecture│   │ Project     │
    └─────────────┘   └─────────────┘   └─────────────┘
```

**Key Insight**: Modules 2, 3, and 4 are **parallel independent subtrees** — they can be researched and built in parallel. Module 5 (Tool Use & Memory) is the **merge node** where ASR, TTS, and LLM outputs integrate. Module 6 (Streaming) is a **cross-cutting concern** that modifies how 2-5 operate.

---

## Node Descriptions

### Module 1: Voice Agents & System Architecture
**Core Question**: What is a voice agent vs chatbot vs conversational AI?

**Key Distinctions**:
| Attribute | Chatbot | Conversational AI | Voice Agent |
|-----------|---------|-------------------|-------------|
| Input modality | Text | Text/voice | Voice-primary |
| Latency tolerance | 2-5s | 1-3s | <500ms |
| Turn-taking | Discrete | Discrete | Continuous |
| Interruption handling | N/A | Limited | Core requirement |
| Tool use | Optional | Common | Essential |

**Citation**: Clark (1996), *Using Language* — action ladder model of dialogue [^35].

---

### Module 2: Speech-to-Text (ASR) Foundations
**Core Question**: How does audio become text?

**Paradigm Spectrum**:
1. **Encoder-only CTC** (Wav2Vec 2.0): Fast, but needs fine-tuning for text mapping [^2].
2. **Encoder-decoder Seq2Seq** (Whisper): General-purpose, robust, higher latency [^1].
3. **Streaming attention** (Deepgram Nova-3): Optimized for real-time, ~100-300ms [^72].

**Research Gap**: Most open-source ASR (Whisper) is batch-oriented. Streaming adaptations (faster-whisper, whisper-streaming) are community efforts without peer-reviewed validation.

---

### Module 3: Text-to-Speech (TTS) & Voice Output
**Core Question**: How does text become natural-sounding speech?

**Architecture Generations**:
1. **Two-stage**: Acoustic model (mel-spectrogram) + Vocoder (WaveRNN/HiFi-GAN). Higher quality, larger footprint [^74].
2. **End-to-end VITS**: Conditional variational autoencoder. Good quality, smaller footprint. Basis of Piper [^13].
3. **LLM-based** (Orpheus, Bark): Generate audio tokens directly. Emerging, higher latency.

**Trade-off Space**:
```
Quality ↑    ┌─────────┐
             │ Eleven  │
             │ Labs    │
             ├─────────┤
             │ Coqui   │
             │ VITS    │
             ├─────────┤
             │ Piper   │
Latency ↓    └─────────┘
             Edge ◄──► Cloud
```

---

### Module 4: LLMs as the Brain
**Core Question**: Why is ASR + TTS alone not enough?

**Answer**: ASR + TTS = "talking search engine." The LLM provides:
- **Reasoning**: Multi-step inference (e.g., "What meetings do I have tomorrow?" → calendar API → synthesize response).
- **Tool orchestration**: Function calling to external systems [^13].
- **Context management**: Conversation history, user preferences, session state.
- **Personality design**: System prompts that shape prosody-implied traits (concise vs expansive).

**Citation**: Yao et al. (2023), ReAct: Synergizing Reasoning and Acting in Language Models [^74].

---

### Module 5: Tool Use, Memory & Agentic Workflows
**Core Question**: What makes a voice system an *agent*?

**Agent Definition** (per Russell & Norvig): An agent is anything that can be viewed as perceiving its environment through sensors and acting upon that environment through actuators [^62].

**For voice agents**:
- **Sensors**: Microphone (audio), VAD (speech detection), STT (transcription).
- **Actuators**: TTS (speech synthesis), tool APIs (calendar, search, calculator).
- **Cognition**: LLM reasoning + memory retrieval.

**Memory Hierarchy**:
| Type | Duration | Storage | Latency |
|------|----------|---------|---------|
| Working memory | Current turn | In-context (prompt) | ~0ms |
| Short-term memory | Session | Redis / local cache | <1ms |
| Long-term memory | Cross-session | Vector DB (FAISS/Qdrant) | 50-300ms → 0.35ms (cached) [^14] |

---

### Module 6: Real-Time Streaming Voice Agents
**Core Question**: How do we get from turn-based to conversational?

**Latency Budget** (human conversation = 200-500ms turn gap):
```
Audio capture:     20-40ms
Network uplink:    30-100ms
STT processing:    184-509ms
LLM TTFT:          200-400ms
TTS TTFB:          200-400ms
Network downlink:  30-100ms
Playback buffer:   20-50ms
─────────────────────────────
Minimum (ideal):   ~700ms
Minimum (streamed):~400ms
```

**Streaming Strategy**: Overlap LLM generation with STT finalization; overlap TTS synthesis with LLM token streaming.

---

### Module 7: Production-Grade Architecture
**Core Question**: How does this survive at scale?

**Required Properties**:
- **Modularity**: Each pipeline stage is a replaceable service.
- **Observability**: RED/USE metrics at every boundary.
- **Resilience**: Circuit breakers, retries, fallback TTS/ASR.
- **Cost control**: GPU time-slicing, CPU fallback, spot instances.
- **Safety**: Content filtering, PII redaction, rate limiting.

---

### Module 8: End-to-End Projects
**Capstone Options**:
1. **AI Receptionist**: Phone-answering, routing, booking. Requires telephony integration (PSTN/SIP).
2. **Meeting Assistant**: Joins calls, takes notes, extracts action items. Requires diarization + ASR.
3. **Research Assistant**: Searches, summarizes, answers complex questions. Requires deep RAG + tool use.
4. **Desktop Assistant**: Controls apps, automates tasks. Requires OS-level integration.
5. **Scheduling Agent**: Calendar management, reminder setting. Requires bi-directional API auth.

---

## Cross-Cutting Concerns

These affect all modules simultaneously:
- **Latency engineering**: P50 vs P99 optimization.
- **Multilingual support**: Whisper covers 99 languages; Piper covers 20+; LLM must match.
- **Privacy**: On-device vs cloud processing decision at every stage.
- **Accessibility**: Real-time captioning, visual feedback, hearing aid compatibility.

---

## References
[^1]: Radford, A., et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision. *arXiv:2212.04356*.
[^2]: Baevski, A., et al. (2020). wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations. *NeurIPS*.
[^7]: Kim, J., Kong, J., & Son, J. (2021). Conditional Variational Autoencoder with Adversarial Learning for End-to-End Text-to-Speech. *ICML*.
[^8]: Shen, J., et al. (2018). Natural TTS Synthesis by Conditioning WaveNet on Mel Spectrogram Predictions. *ICASSP*.
[^13]: OpenAI. (2023). Function Calling API. *OpenAI Platform Documentation*.
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^35]: Clark, H. H. (1996). *Using Language*. Cambridge University Press.
[^62]: Russell, S., & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson.
[^72]: Deepgram. (2024). Nova-3 Streaming ASR Documentation. *Deepgram Developer Docs*.
[^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR*.

[^1]: Clark, H. H. (1996). *Using Language*. Cambridge University Press.
[^2]: Baevski, A., et al. (2020). wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations. *NeurIPS*.
[^3]: Radford, A., et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision. *arXiv:2212.04356*.
[^4]: Deepgram. (2024). Nova-3 Streaming ASR Documentation. *Deepgram Developer Docs*.
[^5]: Shen, J., et al. (2018). Natural TTS Synthesis by Conditioning WaveNet on Mel Spectrogram Predictions. *ICASSP*.
[^6]: Kim, J., Kong, J., & Son, J. (2021). Conditional Variational Autoencoder with Adversarial Learning for End-to-End Text-to-Speech. *ICML*.
[^7]: OpenAI. (2023). Function Calling API. *OpenAI Platform Documentation*.
[^8]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR*.
[^9]: Russell, S., & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson.
[^10]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
