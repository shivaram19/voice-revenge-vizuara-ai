# Architecture Overview: Enterprise Voice Agent Platform

**Version**: 1.0  
**Date**: 2026-04-25  
**Scale Target**: 1,000,000 concurrent sessions  
**Latency Target**: P95 < 500ms turn-gap  

---

## Design Philosophy

> **Modular by contract, scalable by design, observable by default.**

This architecture treats each pipeline stage as an independent service with:
- A defined interface (gRPC/protobuf or REST/OpenAPI)
- A latency Service Level Objective (SLO)
- A fallback degradation path
- RED metrics exported to Prometheus

---

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │   Web App   │     │  Mobile App │     │  Phone/PSTN │                   │
│  │  (WebRTC)   │     │  (WebRTC)   │     │  (SIP/Twilio│                   │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘                   │
└─────────┼───────────────────┼───────────────────┼───────────────────────────┘
          │                   │                   │
          └───────────────────┴───────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────────────┐
│                           EDGE LAYER                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    LiveKit SFU / WebSocket Gateway                   │    │
│  │  - ICE/STUN/TURN handling                                            │    │
│  │  - Audio packet routing (no decode)                                  │    │
│  │  - Simulcast adaptation                                              │    │
│  └─────────────────────────────────┬───────────────────────────────────┘    │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────────┐
│                         INFERENCE ORCHESTRATION                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Agent Controller (Python/FastAPI)                │    │
│  │  - Session state machine                                             │    │
│  │  - Turn detection & barge-in handling                                │    │
│  │  - Pipeline coordination                                             │    │
│  └─────────────────────────────────┬───────────────────────────────────┘    │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│   STT SERVICE   │        │   LLM SERVICE   │        │   TTS SERVICE   │
│  (Distil-Whisper│        │  (vLLM / OAI    │        │  (Piper / Coqui │
│   + VAD)        │        │   compatible)   │        │   + streaming)  │
└────────┬────────┘        └────────┬────────┘        └────────┬────────┘
         │                          │                          │
         │    ┌─────────────────────┘                          │
         │    │                                                │
         │    ▼                                                │
         │ ┌─────────────────┐                                 │
         │ │  MEMORY SERVICE │                                 │
         │ │  (VoiceAgentRAG │                                 │
         │ │   dual-agent)   │                                 │
         │ └─────────────────┘                                 │
         │                                                   │
         └─────────────────────┬─────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────┐
                    │  TOOL EXECUTOR  │
                    │  (MCP Runtime   │
                    │   + sandbox)    │
                    └─────────────────┘
```

---

## Component Definitions

### 1. Client Layer
**Responsibility**: Capture audio, render audio, handle user identity.

**Variants**:
- **WebRTC client**: Browser-based, lowest latency, AEC enabled.
- **Telephony client**: PSTN via Twilio/Vonage, WebSocket media relay.

**State**: None. Clients are thin; all session state lives server-side.

---

### 2. Edge Layer (LiveKit SFU)
**Responsibility**: Route media packets without decoding.

**Why SFU over MCU?**
- **MCU** decodes + mixes + re-encodes: adds 50-100ms latency, high CPU.
- **SFU** forwards packets as-is: adds <5ms, low CPU, scales to 1000s of viewers [^75].

**Scaling**: Horizontal pod autoscaling based on packet throughput.

---

### 3. Agent Controller
**Responsibility**: The "brain stem" of the voice agent.

**State Machine**:
```
[IDLE] ──(VAD speech_start)──► [LISTENING]
[LISTENING] ──(STT final)──► [THINKING]
[THINKING] ──(LLM token)──► [SPEAKING]
[SPEAKING] ──(VAD speech_start)──► [INTERRUPTED] ──► [LISTENING]
[SPEAKING] ──(TTS complete)──► [IDLE]
```

**Key Functions**:
- **Turn detection**: Combine Silero VAD (acoustic) + semantic endpointer (LLM-based) [^34].
- **Barge-in**: On user speech during SPEAKING, abort TTS and switch to LISTENING.
- **Sentence buffering**: Accumulate LLM tokens until sentence boundary, then stream to TTS.

---

### 4. STT Service
**Interface**: gRPC streaming — audio chunks in, transcript events out.

**Event Types**:
- `PartialTranscript`: Interim result (for UI feedback only).
- `FinalTranscript`: Committed text (sent to LLM).
- `SpeechFinal`: End-of-utterance detected.

**Implementation**: Distil-Whisper via faster-whisper on GPU (English) or CPU (edge).

**SLO**: P95 < 300ms from final audio to transcript.

---

### 5. LLM Service
**Interface**: OpenAI-compatible `/v1/chat/completions` with `stream=true`.

**Deployment**: vLLM on GPU cluster with continuous batching.

**Optimization**: **Speculative generation** — start inference on partial transcript before STT finalizes. Abort and restart on final transcript if divergence > threshold.

**SLO**: TTFT < 200ms; throughput > 20 tokens/s.

---

### 6. TTS Service
**Interface**: gRPC streaming — text sentences in, audio chunks out.

**Implementation**: Piper TTS (edge/local) or Coqui VITS (cloud quality).

**Streaming Strategy**: Sentence-level chunking. Start synthesis at first complete sentence while LLM continues generating.

**SLO**: TTFB < 150ms per sentence.

---

### 7. Memory Service
**Interface**: Internal — queried by Agent Controller before LLM call.

**Implementation**: VoiceAgentRAG dual-agent pattern [^14].
- Fast Talker: FAISS in-memory cache (sub-ms lookup).
- Slow Thinker: Background async prefetch to Qdrant.

**SLO**: Cache hit < 1ms; cache miss < 100ms (with fallback to no-RAG).

---

### 8. Tool Executor
**Interface**: MCP (Model Context Protocol) + sandboxed function runtime.

**Safety**:
- Functions run in ephemeral containers (2s timeout).
- PII redaction on all inputs/outputs.
- Idempotency keys prevent double-execution.

---

## Data Flow: A Complete Turn

```
Time →

User speaks:     [==========]
VAD detects:         [==]
STT streams:         [====]
STT final:               [*]
Memory retrieval:         [==]
LLM TTFT:                  [*]
LLM generates:              [===========]
TTS TTFB (1st sentence):       [*]
TTS streams:                    [==========]
User hears:                      [==========]

Timeline:        0   100  200  300  400  500  600  700  800  900 (ms)
```

**Perceived latency** = time from user stop speaking to first audible response ≈ 400-600ms.

---

## Scaling Strategy

### Horizontal Scaling
| Service | Bottleneck | Scale Trigger | Target |
|---------|-----------|---------------|--------|
| SFU | Packet throughput | CPU > 70% | Add SFU node |
| STT | GPU memory | Queue depth > 5 | Add GPU pod |
| LLM | Token throughput | TTFT P95 > 250ms | Add GPU pod |
| TTS | RTF | RTF > 0.5× | Add CPU pod |

### Cost Optimization
1. **GPU time-slicing**: Run STT + TTS on same GPU via MPS if underutilized.
2. **Spot instances**: Batch analytics (post-call transcription) on preemptible nodes.
3. **CPU fallback**: Distil-Whisper on CPU for low-traffic hours.
4. **Model quantization**: INT8 for STT, FP16 for LLM, INT8 for TTS.

**Citation**: NVIDIA (2023), "Autoscaling Riva Deployment with Kubernetes" [^31]; Barroso et al. (2018) [^30].

---

## Failure Modes & Degradation

| Failure | Detection | Degradation |
|---------|-----------|-------------|
| STT timeout | P95 > 500ms | Switch to cloud API (Deepgram) |
| LLM timeout | TTFT > 500ms | Return cached "thinking" audio; retry |
| TTS timeout | TTFB > 300ms | Switch to simpler voice; increase speed |
| Memory miss | Cache miss > 50% | Disable RAG; use LLM context only |
| Network loss | Packet loss > 5% | Reduce bitrate; enable FEC |

---

## References

[^75]: UGent thesis (2023). SFU vs MCU analysis.
[^34]: Phoenix-VAD (2025). Semantic endpoint detection for full-duplex interaction. *arXiv:2509.20410*.
[^14]: Qiu et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^31]: NVIDIA. (2023). Autoscaling Riva Deployment with Kubernetes.
[^30]: Barroso, L. A., et al. (2018). *The Datacenter as a Computer*.
