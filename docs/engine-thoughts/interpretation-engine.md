# Interpretation Engine: How Research Is Perceived & Synthesized

This document is the "meta-layer" — it records not just *what* was found, but *how* it is being perceived, connected, and weighted by the architectural cognition engine. This is where raw research becomes structured intelligence.

---

## Perception Framework

### Signal vs Noise Classification

When processing the research corpus, each source is classified by signal quality:

| Tier | Source Type | Weight | Examples |
|------|-------------|--------|----------|
| **T1** | Peer-reviewed paper / Official RFC / Canonical book | 1.0 | Whisper paper (Radford et al., 2022), RFC 6455, SRE Book |
| **T2** | Industry benchmark / Production blog with metrics | 0.8 | LiveKit architecture blog, ElevenLabs latency measurements |
| **T3** | Open-source documentation / Verified GitHub repo | 0.6 | faster-whisper README, piper-tts docs |
| **T4** | Opinion / Unverified blog / Marketing material | 0.2 | Generic "AI will change everything" articles |

**Rule**: No T4 source can be the *primary* justification for an architectural decision. T4 can only support T1-T3.

---

## Pattern Recognition: Emergent Themes

### Theme 1: The Latency Wall

**Perception**: Across all research, sub-200ms is the conversational threshold. But the *sum* of individual component latencies exceeds this budget:

| Component | Latency | Source Tier |
|-----------|---------|-------------|
| STT (streaming) | 184-509ms | T2 (Deepgram benchmarks) |
| LLM TTFT | 337ms | T2 (vLLM on A10G) |
| TTS TTFB | 219-236ms | T2 (ElevenLabs) |
| **Sequential Sum** | **~1000ms** | — |

**Synthesis Insight**: The only path to sub-500ms is **not** faster individual components — it is **pipeline overlap** (streaming). This is the central architectural insight derived from the research corpus.

**Citation**: SigArch (2026), "Building Enterprise Realtime Voice Agents from Scratch" [^16] formally proves: `T_streaming = T_STT + T_LLM_first_sentence + T_TTS_TTFB ≈ 900ms` with naive streaming, and sub-500ms requires speculative/preemptive generation.

---

### Theme 2: The Modularity Paradox

**Perception**: Native speech-to-speech models (GPT-4o realtime, Moshi) promise lower latency (~200-400ms) but create **vendor lock-in** and **observability darkness**. Cascaded pipelines (STT→LLM→TTS) are modular, inspectable, and swappable — but higher latency.

**Synthesis Insight**: This is not an either/or. The correct architecture is **cascaded-by-default with S2S escape hatch**. Design the pipeline so that swapping a cascaded stage for a native S2S model is a configuration change, not a rewrite.

**Citation**: LiveKit (2026), "Pipeline vs Realtime" comparison table [^17]; Chanl.ai (2026) production architecture [^19].

---

### Theme 3: The RAG Latency Trap

**Perception**: RAG is standard for knowledge grounding. But vector DB queries add 50-300ms — which, in a voice pipeline, consumes the *entire* latency budget.

**Synthesis Insight**: The Salesforce VoiceAgentRAG paper (2026) [^14] provides the architectural answer: a **dual-agent memory router**.
- **Slow Thinker** (background): Predicts follow-up topics, pre-fetches into FAISS cache.
- **Fast Talker** (foreground): Reads only from sub-millisecond cache.
- Result: 316× retrieval speedup (110ms → 0.35ms), 75% cache hit rate.

This is not an optimization — it is a **paradigm shift** in how memory works for real-time systems.

---

### Theme 4: The Edge-Center Spectrum

**Perception**: Three forces pull in different directions:
1. **Privacy** → On-device (Whisper.cpp, Piper TTS on Raspberry Pi)
2. **Quality** → Cloud GPU (Whisper large-v3, ElevenLabs)
3. **Cost** → Hybrid (Distil-Whisper on CPU for English, cloud for multilingual)

**Synthesis Insight**: The architecture is **topology-aware**. The same voice agent runs across edge, hybrid, and cloud deployments without code changes:
- Fully local (edge) for privacy-sensitive deployments
- Hybrid for cost optimization
- Fully cloud for maximum quality

This requires **interface abstraction** at every layer. The LLM reasoning layer does not know whether ASR ran on-device or in the cloud, per hexagonal architecture principles where domain logic depends on ports, not adapters [^42].

**Citation**: Hansen (2023), Piper TTS on Raspberry Pi 4 [^48]; Gandhi et al. (2023), Distil-Whisper 5.8× speedup [^3].

---

## Bidirectional Connection Matrix

How decisions in one domain propagate to others:

```
ASR Model Selection ─────┬─────► Latency Budget
                         │       ├─► TTS Quality Trade-off
                         │       └─► Infrastructure (GPU vs CPU)
                         │
                         ├─────► Streaming Architecture
                         │       ├─► WebRTC vs WebSocket
                         │       └─► Buffer sizing
                         │
                         └─────► Memory Strategy
                                 ├─► Context window size
                                 └─► RAG cache hit rate
```

### Concrete Example: Choosing Distil-Whisper

**Decision**: Use Distil-Whisper for English ASR in production.

**Downstream impacts**:
1. **Latency**: 5.8× faster than Whisper → frees 300ms for LLM/TTS budget.
2. **Infrastructure**: Can run on CPU for 10-20 concurrent streams → reduces GPU node count by ~40%.
3. **Quality**: WER within 1% on OOD data → acceptable for conversational use.
4. **Memory**: Faster ASR → more frequent transcript updates → LLM context updates more often → need for efficient context compression.
5. **TTS**: ASR latency savings allow higher-quality TTS (e.g., Piper "high" voice instead of "medium").

**Citation**: Gandhi et al. (2023) [^3]; LiteASR (2025) [^59].

---

## Cognitive Biases Guarded Against

| Bias | Manifestation | Guard |
|------|--------------|-------|
| **Recency bias** | Overweighting 2026 papers, underweighting 2017 Transformers | Weight by citation count + replication |
| **Hype bias** | Assuming newest = best | Require latency/quality metrics, not just claims |
| **Not-invented-here** | Rejecting commercial APIs | TCO analysis must include engineering time |
| **Sunk cost** | Sticking with chosen stack | Every ADR has a "revisit trigger" condition |
| **Confirmation** | Citing only supporting research | Every ADR requires at least one counter-argument |

---

## Uncertainty Register

Questions where the research is inconclusive:

| Question | Current Stance | Confidence | Needed Evidence |
|----------|---------------|------------|-----------------|
| Is speculative decoding worth the complexity for voice ASR? | Likely yes for large-v3, no for Distil-Whisper | 6/10 | Production benchmark with real audio |
| Should VAD be semantic (LLM-based) or acoustic (Silero)? | Hybrid: Silero for detection, lightweight LLM for turn-completion | 5/10 | A/B test on interruption accuracy |
| Is event sourcing overkill for conversation history? | No — it enables replay, audit, and async analytics | 7/10 | Latency benchmark with Kafka vs PostgreSQL |
| Mamba vs Transformer for TTS? | Transformer for now; Mamba evaluation in Q3 | 4/10 | CMOS comparison on same dataset |

---

## References
[^3]: Gandhi, S., et al. (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. *arXiv:2311.00430*.
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG: Solving the RAG Latency Bottleneck in Real-Time Voice Agents. *arXiv:2603.02206*.
[^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. *arXiv:2603.05413*.
[^17]: LiveKit. (2026). Pipeline vs. Realtime — Which is the better Voice Agent Architecture? *LiveKit Blog*.
[^19]: Chanl.ai. (2026). Voice Agent Platform Architecture: The Stack Behind Sub-300ms Responses. *Chanl.ai Blog*.
[^42]: Cockburn, A. (2005). Hexagonal Architecture. *alistair.cockburn.us*.
[^48]: Hansen, M. (2023). Piper: A fast, local neural text-to-speech system. *GitHub: rhasspy/piper*.
[^59]: LiteASR. (2025). Efficient Automatic Speech Recognition with Low-Rank Approximation. *arXiv:2502.20583*.

[^1]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. *arXiv:2603.05413*.
[^2]: LiveKit. (2026). Pipeline vs. Realtime — Which is the better Voice Agent Architecture? *LiveKit Blog*.
[^3]: Chanl.ai. (2026). Voice Agent Platform Architecture: The Stack Behind Sub-300ms Responses. *Chanl.ai Blog*.
[^4]: Qiu, J., et al. (2026). VoiceAgentRAG: Solving the RAG Latency Bottleneck in Real-Time Voice Agents. *arXiv:2603.02206*.
[^5]: Hansen, M. (2023). Piper: A fast, local neural text-to-speech system. *GitHub: rhasspy/piper*.
[^6]: Gandhi, S., et al. (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. *arXiv:2311.00430*.
[^7]: LiteASR. (2025). Efficient Automatic Speech Recognition with Low-Rank Approximation. *arXiv:2502.20583*.
[^8]: Cockburn, A. (2005). Hexagonal Architecture. *alistair.cockburn.us*.
