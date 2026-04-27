# DFS-02: Transport Protocols — WebRTC vs WebSocket vs gRPC

**Research Phase**: DFS traversal from Streaming node  
**Scope**: Real-time audio transport for voice agents  
**Date**: 2026-04-25

---

## Problem Statement

Voice AI requires **full-duplex, low-latency audio streaming** between client and server. The transport protocol choice is the most consequential architectural decision because it affects:
1. Latency (mouth-to-ear delay)
2. Scalability (concurrent connections per server)
3. Interruption handling (barge-in)
4. Infrastructure complexity

---

## Protocol Comparison

### WebSocket (RFC 6455)

**Mechanism**: Upgrades HTTP to persistent TCP socket. Full-duplex text/binary messaging.

**Properties**:
| Property | Value |
|----------|-------|
| Transport | TCP |
| Latency | ~10-50ms for data |
| Packet loss | Retransmits (head-of-line blocking) |
| Media features | None (raw bytes only) |
| Encryption | TLS (wss://) |
| Firewall | Works over HTTPS ports (443) |
| Scaling | Horizontal via load balancers |

**Voice Agent Suitability**:
- ✅ Simple to implement (Python `websockets`, Node `ws`).
- ✅ Easy to inspect/debug (text frames).
- ❌ No built-in acoustic echo cancellation (AEC) — barge-in is hard.
- ❌ TCP head-of-line blocking causes jitter under packet loss.
- ❌ Must implement jitter buffer, packet loss concealment manually.

**Best for**: Server-to-server audio relay, telephony gateways (Twilio uses WebSocket for media streams), corporate networks with strict firewalls [^21].

---

### WebRTC (IETF Standards: RFC 8829, RFC 8830, etc.)

**Mechanism**: Peer-to-peer UDP-based media transport with NAT traversal (STUN/TURN/ICE).

**Properties**:
| Property | Value |
|----------|-------|
| Transport | UDP (SRTP for media, SCTP for data) |
| Latency | ~60-150ms P2P; ~100-300ms via SFU |
| Packet loss | Skips (stream continues with PLC) |
| Media features | Built-in AEC, noise suppression, AGC |
| Encryption | Mandatory DTLS-SRTP |
| Firewall | May need TURN relay for strict NAT |
| Scaling | Requires SFU/MCU for >2 parties |

**SFU (Selective Forwarding Unit)**:
The critical scaling component for voice AI. An SFU:
- Routes RTP packets without decoding/re-encoding.
- Enables simulcast (different quality per subscriber).
- Provides observability (packet loss, jitter per participant).

**Citation**: UGent thesis (2023), comparative analysis of P2P vs MCU vs SFU [^55].

**Voice Agent Suitability**:
- ✅ Built-in AEC enables barge-in (user can interrupt agent).
- ✅ UDP handles packet loss gracefully for audio.
- ✅ Browser-native (no plugins).
- ❌ Complex to implement from scratch (use LiveKit, mediasoup).
- ❌ Signaling server required (often WebSocket).

**Best for**: Browser-based voice agents, real-time conversational AI, multi-party meetings [^17].

---

### gRPC Streaming

**Mechanism**: HTTP/2-based bidirectional streaming with Protocol Buffers.

**Properties**:
| Property | Value |
|----------|-------|
| Transport | HTTP/2 over TCP |
| Latency | ~5-20ms for RPC |
| Streaming | Bidirectional, multiplexed |
| Schema | Strongly typed (Protobuf) |
| Tooling | Excellent code generation |

**Voice Agent Suitability**:
- ✅ Excellent for server-to-server streaming (STT → LLM → TTS pipeline).
- ✅ Strong typing reduces integration bugs.
- ❌ Not designed for raw media; adds framing overhead.
- ❌ Browser support requires gRPC-Web (WebSocket fallback).

**Best for**: Internal microservice communication, not client-facing audio [^66].

---

## Benchmark Data

| Study | WebRTC Latency | WebSocket Latency | Notes |
|-------|---------------|-------------------|-------|
| ResearchGate (2024) | ~150ms | ~200ms | Lower CPU/network for WebRTC |
| LiveKit (2026) | ~100-300ms via SFU | N/A | Simulcast adapts to bandwidth |
| Skywork.ai (2025) | ~220-400ms (Realtime API) | ~300-500ms | Includes inference time |

**Citation**: ResearchGate comparative study [^67]; LiveKit blog [^17]; Skywork.ai [^68].

---

## Architectural Decision Matrix

| Scenario | Protocol | Justification |
|----------|----------|---------------|
| Browser client → Agent | **WebRTC** | AEC for barge-in; native support |
| Agent internal pipeline | **gRPC** | Type-safe; fast; service mesh ready |
| Telephony/PSTN bridge | **WebSocket** | Firewall-friendly; Twilio-compatible |
| Server→Server audio relay | **WebSocket or RTP** | Simplicity; existing VoIP infra |
| Mobile app (native) | **WebRTC** | Same benefits as browser |

---

## Hybrid Architecture Pattern

Production systems typically use **all three**:

```
┌─────────────┐     WebRTC      ┌─────────────┐
│   Browser   │◄───────────────►│  LiveKit    │
│   Client    │   (media)       │    SFU      │
└─────────────┘                 └──────┬──────┘
                                       │
                              WebSocket│(signaling)
                                       │
                              ┌────────▼────────┐
                              │  Agent Service  │
                              │  (Python/Node)  │
                              └────────┬────────┘
                                       │
                              gRPC     │
                              streaming│
                                       │
                              ┌────────▼────────┐
                              │  STT Service    │
                              │  LLM Service    │
                              │  TTS Service    │
                              └─────────────────┘
```

**Citation**: This pattern is documented in LiveKit Agents architecture [^69] and Chanl.ai production stack [^19].

---

## References
[^17]: LiveKit. (2026). Why WebRTC beats WebSockets for realtime voice AI. *LiveKit Blog*.
[^19]: Chanl.ai. (2026). Voice Agent Platform Architecture.
[^21]: Fette, I., & Melnikov, A. (2011). RFC 6455: The WebSocket Protocol. *IETF*.
[^55]: Van Landuyt, D. (2023). A Comparative Study of WebRTC and WebSocket. *Ghent University Thesis*.
[^66]: gRPC Authors. (2023). gRPC Core Documentation. *grpc.io*.
[^67]: ResearchGate. (2024). A Comparative Study of WebRTC and WebSocket Performance in Real-Time Voice Communication.
[^68]: Skywork.ai. (2025). OpenAI Realtime API vs WebRTC 2025.
[^69]: LiveKit. (2025). LiveKit Agents Framework Documentation.

[^1]: Fette, I., & Melnikov, A. (2011). RFC 6455: The WebSocket Protocol. *IETF*.
[^2]: Van Landuyt, D. (2023). A Comparative Study of WebRTC and WebSocket. *Ghent University Thesis*.
[^3]: LiveKit. (2026). Why WebRTC beats WebSockets for realtime voice AI. *LiveKit Blog*.
[^4]: gRPC Authors. (2023). gRPC Core Documentation. *grpc.io*.
[^5]: ResearchGate. (2024). A Comparative Study of WebRTC and WebSocket Performance in Real-Time Voice Communication.
[^6]: Skywork.ai. (2025). OpenAI Realtime API vs WebRTC 2025.
[^7]: LiveKit. (2025). LiveKit Agents Framework Documentation.
[^8]: Chanl.ai. (2026). Voice Agent Platform Architecture.
