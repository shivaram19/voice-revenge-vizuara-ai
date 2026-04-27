# BIDIR-01: Latency ↔ Architecture Co-Design

**Research Phase**: Bidirectional impact mapping  
**Scope**: How latency constraints force architectural inversions  
**Date**: 2026-04-25

---

## Core Thesis

> Latency is not a metric to optimize — it is a **design constraint that inverts traditional software architecture**.

In conventional web applications, we accept 100-500ms response times. In voice AI, exceeding 500ms breaks the conversational illusion. This constraint forces us to violate standard best practices and invent new patterns.

---

## The Latency Budget Equation

### Sequential Pipeline (Non-Streaming)
```
T_total = T_capture + T_network_up + T_STT + T_LLM + T_TTS + T_network_down + T_playback

T_total ≈ 40 + 50 + 400 + 800 + 400 + 50 + 40 = 1780ms
```
**Verdict**: Unusable. This is a "talking search engine," not a conversation.

### Streaming Pipeline (Basic Overlap)
```
T_streaming = T_STT_final + T_LLM_first_sentence + T_TTS_TTFB
T_streaming ≈ 400 + 300 + 200 = 900ms
```
**Verdict**: Noticeable but functional. Perceived latency is reduced because TTS starts before LLM finishes.

### Streaming Pipeline (Optimized)
```
T_optimized = T_STT_final + T_LLM_TTFT + T_TTS_first_chunk
T_optimized ≈ 300 + 200 + 150 = 650ms
```
**Verdict**: Conversational. Requires:
- Streaming STT (partial → final transcript without waiting for silence)
- Speculative LLM generation (start inference on partial transcript)
- Streaming TTS (synthesize sentence fragments)

**Citation**: SigArch (2026) [^16]; Gokuljs (2026) [^18].

---

## Architectural Inversions Forced by Latency

### Inversion 1: Eager Execution Over Lazy Evaluation

**Standard practice**: Wait for complete user input before processing.
**Voice requirement**: Begin LLM inference on **interim transcripts** before STT finalizes.

**Risk**: LLM generates response based on incorrect partial transcript. This occurs in 15-30% of speculative generations depending on utterance complexity [^16].
**Mitigation**: Abort and restart on final transcript; use lightweight LLM for speculative path. Validation threshold: discard speculative output if transcript divergence > 20% [^16].

**Pattern**: *Speculative Generation with Validation*

---

### Inversion 2: Cache Pre-warming Over On-Demand Retrieval

**Standard practice**: Query database when user asks.
**Voice requirement**: Pre-fetch context before user finishes speaking.

**Implementation**: VoiceAgentRAG dual-agent architecture [^3]:
- **Slow Thinker** (background): Predicts follow-up topics during current response.
- **Fast Talker** (foreground): Serves from sub-millisecond cache.

**Result**: 316× retrieval speedup; 75% cache hit rate.

---

### Inversion 3: Lossy Context Over Perfect Recall

**Standard practice**: Send full conversation history to LLM.
**Voice requirement**: Context window is limited; latency increases with prompt length.

**Implementation**:
- Compress conversation history to salient points (LLM summarization every N turns).
- Maintain separate "working memory" (last 3 turns) and "episodic memory" (summarized).
- Drop oldest turns when approaching token limit.

**Trade-off**: Occasional loss of nuance vs. consistent sub-second response.

---

### Inversion 4: Push Over Pull

**Standard practice**: Client polls or requests data.
**Voice requirement**: Server must push audio chunks as soon as synthesized.

**Pattern**: WebSocket/WebRTC streaming with **Server-Sent Events** or **RTP packet streaming**.

---

## Cross-Domain Impact Matrix

| Decision in Domain A | Impact on Domain B | Magnitude |
|----------------------|-------------------|-----------|
| Choose Distil-Whisper (ASR) | Frees 300ms for TTS quality | High |
| Choose Piper TTS (edge) | Eliminates network downlink latency | Medium |
| Add RAG retrieval | Adds 50-300ms unless cached | Critical |
| Use WebRTC vs WebSocket | Enables barge-in (saves 200-500ms interruption detection) | High |
| GPU autoscaling cold start | Adds 5-30s to first request — requires pre-warming | High |
| Conversation history length | Linear increase in LLM TTFT | Medium |

---

## Cost-Latency Pareto Frontier

There is no free lunch. The Pareto frontier for voice agents:

```
Latency (ms)
   ↑
2000│                                    ● Batch API (cheapest)
    │
1000│              ● Optimized streaming
    │
 500│    ● Conversational target
    │
 200│ ● Native S2S (GPT-4o)      ● Best cascaded
    │                               (expensive)
    └────────────────────────────────────────→ Cost ($/min)
         Low                          High
```

**Insight**: Native speech-to-speech models (GPT-4o realtime, Moshi) are the only path to sub-200ms. But they sacrifice modularity, observability, and cost control. The cascaded pipeline can reach 400-600ms at 1/5th the cost.

**Citation**: LiveKit (2026), "Pipeline vs Realtime" [^17]; Chanl.ai (2026) [^19].

---

## Co-Design Checklist

Before changing any single component, answer:

1. **Latency**: How does this change the critical path? (ms)
2. **Cost**: How does this change TCO at 1,000 concurrent users? ($/hr)
3. **Quality**: How does this change WER / CMOS / user satisfaction?
4. **Scale**: Does this introduce a bottleneck at 10× load?
5. **Fallback**: What happens when this component degrades?
6. **Observability**: Can we measure the impact in production?

---

## References
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^16]: SigArch. (2026). Section 4.2. Speculative generation abort rates measured on streaming pipelines with partial transcripts. *arXiv:2603.05413*.
[^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. *arXiv:2603.05413*.
[^16]: SigArch. (2026). Section 4.2. Speculative generation abort rates measured on streaming pipelines with partial transcripts. *arXiv:2603.05413*.
[^17]: LiveKit. (2026). Pipeline vs. Realtime. *LiveKit Blog*.
[^17]: LiveKit. (2026). Pipeline vs. Realtime. *LiveKit Blog*.
[^18]: Gokuljs. (2026). How Real-Time Voice Agents Work: Architecture and Latency. *gokuljs.com*.
[^18]: Gokuljs. (2026). How Real-Time Voice Agents Work: Architecture and Latency. *gokuljs.com*.
[^19]: Chanl.ai. (2026). Voice Agent Platform Architecture.
[^19]: Chanl.ai. (2026). Voice Agent Platform Architecture.

[^1]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. *arXiv:2603.05413*.
[^2]: Gokuljs. (2026). How Real-Time Voice Agents Work: Architecture and Latency. *gokuljs.com*.
[^3]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^4]: LiveKit. (2026). Pipeline vs. Realtime. *LiveKit Blog*.
[^5]: Chanl.ai. (2026). Voice Agent Platform Architecture.
[^6]: SigArch. (2026). Section 4.2. Speculative generation abort rates measured on streaming pipelines with partial transcripts. *arXiv:2603.05413*.
