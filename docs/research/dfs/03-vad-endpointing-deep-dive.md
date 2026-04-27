# DFS-03: Voice Activity Detection & Turn-Taking

**Research Phase**: DFS traversal from Real-Time Streaming node  
**Scope**: VAD algorithms, endpointing, semantic detection, barge-in  
**Date**: 2026-04-25

---

## Problem Definition

Voice agents must answer three questions continuously:
1. **Is the user speaking?** (VAD — acoustic detection)
2. **Has the user finished their turn?** (Endpointing — timing/semantic)
3. **Is the user interrupting me?** (Barge-in — full-duplex handling)

Getting any of these wrong destroys the conversational illusion.

---

## VAD Taxonomy

### Generation 1: Energy-Based (1975)
**Method**: Threshold on signal amplitude / zero-crossing rate.
**Pros**: Trivial computation, no training data.
**Cons**: Fails in noise, music, breath sounds.
**Status**: Obsolete for production voice AI.

**Citation**: Rabiner & Sambur (1975), Bell System Technical Journal [^32].

---

### Generation 2: Statistical / GMM-HMM (1990s-2010s)
**Method**: Model speech vs noise as Gaussian mixtures. Hidden Markov Model for state transitions.
**Pros**: Robust to moderate noise.
**Cons**: Requires domain-specific tuning; doesn't generalize.

---

### Generation 3: Deep Learning (2018-present)
**Method**: Neural networks (LSTM, CNN, Transformer) trained on labeled speech/noise data.
**Pros**: High accuracy across noise conditions; language-independent.
**Cons**: Requires GPU for batch; CPU feasible for small models.

**Representative: Silero VAD**
- **Architecture**: LSTM-based.
- **Latency**: <1ms per chunk on single CPU thread [^33].
- **Accuracy**: 5% turn miss rate vs 17% for Google Speech API (Hazumi1911 dataset) [^78].
- **Integration**: Used by LiveKit, NVIDIA Riva, LocalAI.

**Citation**: Silero Team (2024) [^33]; IWLSDS 2025 analysis [^78].

---

### Generation 4: Semantic VAD (2024-present)
**Method**: Use ASR + lightweight LLM to determine if utterance is semantically complete.
**Pros**: Understands context — "I'll have the... uh..." is incomplete even during silence.
**Cons**: Adds LLM latency; overkill for simple commands.

**Representative: Phoenix-VAD**
- **Architecture**: Streaming transformer predicting "Continue Speaking" vs "Stop Speaking".
- **Integration**: Works with full-duplex dialogue models.

**Citation**: Phoenix-VAD (2025) [^34].

---

## Comparative Analysis

| Model | Type | Latency | Turn Miss Rate | Noise Robustness |
|-------|------|---------|----------------|------------------|
| Energy threshold | Classical | ~0ms | ~30% | Poor |
| Google Speech API | Streaming ASR | ~100ms | 17% [^78] | Good |
| Silero VAD | LSTM | <1ms [^33] | 5% [^78] | Excellent |
| Pyadin (DNN-HMM) | Hybrid | ~10ms | 2% [^78] | Excellent |
| Phoenix-VAD | Semantic | ~50ms | <2% (est) | Excellent |

**Key Insight**: For voice agents, **Silero VAD is the sweet spot** — fast enough to not add latency, accurate enough for production, and open-source.

---

## Turn-Taking Architecture

### The Human Baseline
Human conversation operates on **200-500ms turn-taking rhythms** across cultures [^35]. This is our ceiling.

### System Design: Cascaded Detection

```
Audio Stream
     │
     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Silero VAD │────►│  ASR Final  │────►│  Semantic   │
│  (acoustic) │     │  (stable    │     │  Check      │
│             │     │  transcript)│     │  (tier 3)   │
└─────────────┘     └─────────────┘     └─────────────┘
     │
     ▼
Speech Start ──► Begin ASR streaming
Speech End   ──► Trigger LLM (after ASR final)
```

**Latency Budget**:
- VAD detection: <1ms
- ASR finalization: 100-300ms (depends on endpointing patience)
- **Total before LLM**: 100-300ms

---

## Barge-In Handling

Barge-in = user speaks while agent is speaking. This requires **full-duplex** operation.

### Challenge: Echo
The agent's own speech feeds back into the microphone. Without cancellation, VAD fires continuously.

### Solution: Acoustic Echo Cancellation (AEC)
**WebRTC provides built-in AEC** [^69]. This is the primary reason to use WebRTC over WebSocket for client transport.

### Barge-In Pipeline
```
Agent is SPEAKING
     │
     ▼
User starts speaking ──► AEC removes agent audio ──► VAD detects user speech
                                                          │
                                                          ▼
                                               Abort TTS stream immediately
                                               Flush LLM generation
                                               Transition to LISTENING
```

**Critical Path**: VAD → Abort must complete in <50ms to feel responsive.

---

## Endpointing Strategies

### Strategy 1: Fixed Silence Duration
**Method**: After VAD detects silence, wait N ms before triggering LLM.
**Pros**: Simple, predictable.
**Cons**: Too short = cuts off trailing words; too long = adds latency.
**Optimal N**: 300-500ms for natural speech [^70].

### Strategy 2: ASR Confidence-Based
**Method**: Trigger when ASR returns `is_final=True` and `speech_final=True`.
**Pros**: Leverages model's internal confidence.
**Cons**: ASR delays finalization in ambiguous cases. Deepgram Nova-3 exhibits 184-509ms variance in finalization latency depending on acoustic confidence [^70].

### Strategy 3: Hybrid (Recommended)
**Method**: 
1. Wait for VAD silence (>300ms).
2. Check ASR `speech_final`.
3. (Optional) Lightweight semantic check: "Does this utterance grammatically complete?"

**Citation**: This hybrid approach is used by Deepgram Nova-3 and recommended in Phoenix-VAD [^34].

---

## Research Gaps

1. **No open benchmark for barge-in latency**: We need a dataset measuring "time from user interruption to system response halt."
2. **Cross-talk detection**: When two humans speak simultaneously (e.g., in meeting assistant), current VADs struggle.
3. **Emotional endpointing**: Users trail off when uncertain. Semantic VAD detects hedging language via lightweight LLM classification of utterance completeness [^34].

---

## References

[^32]: Rabiner, L. R., & Sambur, M. R. (1975). An Algorithm for Determining the Endpoints of Isolated Utterances. *BSTJ*.
[^33]: Silero Team. (2024). Silero VAD. *GitHub*.
[^78]: IWLSDS 2025. Analysis of Voice Activity Detection Errors in API-based Dialogue Systems.
[^34]: Phoenix-VAD. (2025). Streaming Semantic Endpoint Detection. *arXiv:2509.20410*.
[^35]: Clark, H. H. (1996). *Using Language*. Cambridge.
[^69]: WebRTC.org. (2023). Acoustic Echo Cancellation documentation.
[^70]: Deepgram. (2024). Endpointing configuration best practices.
