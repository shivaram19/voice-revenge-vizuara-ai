# ADR-024: WebRTC Transport for Self-Hosted ASR

**Date:** 2026-05-02  
**Status:** Approved  
**Scope:** Choose the browser-to-server media transport for the Moonshine v2 real-time ASR demo  
**Risk Level:** Medium

---

## Context

For the self-hosted ASR demo, browser microphone audio must reach the server with minimal latency. Candidate transports:

1. **WebSocket with μ-law/PCM** — used by Twilio Media Streams today; simple but adds framing overhead and typically runs on a second TCP connection.
2. **WebRTC audio track + DataChannel** — browser-native, peer-to-peer media path; RTP/UDP reduces head-of-line blocking; DataChannel returns transcripts on the same peer connection.
3. **WebRTC audio track + WebSocket side channel** — separates media and control; more firewall-friendly but adds a second connection.

## Decision

Use **WebRTC audio track ingestion with RTCDataChannel transcript delivery**.

Rationale:
- WebRTC is the standard for browser real-time media (RFC 8829) and avoids the ~100-300ms jitter buffers common in TCP-based WebSocket streaming [^aiortc].
- A single peer connection carries both upstream audio and downstream transcript events, simplifying session management.
- aiortc provides a mature Python server-side implementation, avoiding a Node.js shim.
- Audio is resampled server-side to 16 kHz mono with `scipy.signal.resample_poly` before being fed to Moonshine.

Server-side flow:

```
Browser mic ──► aiortc RTCRtpReceiver ──► PyAV decode ──► resample 16kHz mono
                                                       │
                                                       ▼
                                               Moonshine v2 Stream
                                                       │
                                                       ▼
                                               RTCDataChannel ──► Browser UI
```

## Consequences

### Positive
- Sub-200ms glass-to-glass latency target is achievable when combined with Moonshine's native streaming.
- Browser demo requires no plugins; HTTPS + getUserMedia are sufficient on modern browsers.
- DataChannel preserves event ordering with `ordered: true`, matching Deepgram-style partial/final transcript semantics.

### Negative
- WebRTC requires HTTPS in production and TURN for symmetric NAT traversal, increasing operational cost.
- aiortc's resampling path depends on `scipy` and `av`; container must include ffmpeg/libav.
- ICE failures behind corporate firewalls are harder to debug than plain TCP WebSocket errors.

### Risks
- **Browser compatibility:** Safari and Firefox may enforce different codec/SDP rules; opus is mandatory and universally supported.
- **GPU container networking:** GPU node pools may not expose public UDP ports, requiring TURN relay.
- **No built-in echo cancellation server-side:** browser-side AEC must be enabled via `echoCancellation: true` constraints.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|---|---|---|---|
| WebSocket μ-law (reuse Twilio path) | Existing handler, firewall-friendly | TCP head-of-line blocking, separate transcript channel | Higher latency; not idiomatic for browser media |
| WebRTC audio + WebSocket transcripts | Simpler transcript fanout | Two connections, harder NAT traversal | Doesn't leverage WebRTC's unified connection model |
| gRPC with WebTransport | Modern, low overhead | Limited browser support, complex ops | Not production-ready across all target browsers |
| Raw UDP/RTP custom server | Minimal overhead | Must reimplement ICE, DTLS, SRTP | Reinventing WebRTC |

## References

- [^aiortc]: Holm, J., et al. (2019-). aiortc — WebRTC and ORTC implementation for Python using asyncio. https://github.com/aiortc/aiortc.
- [^RFC8829]: Alvestrand, H. (2021). WebRTC 1.0: Real-Time Communication Between Browsers. *W3C Recommendation* / *RFC 8829*.
- [^Moonshine2026]: King, E., et al. (2026). Moonshine v2: Ergodic Streaming Encoder ASR for Latency-Critical Speech Applications. *arXiv:2602.12241*.

## Metrics

- `webrtc_connections_total` — counter of negotiated peer connections
- `webrtc_connection_duration_seconds` — histogram of session lifetime
- `webrtc_datachannel_messages_sent_total` — counter, labeled by event type
- `webrtc_ice_connection_failures_total` — counter of failed ICE negotiations
- Target: <5% ICE failure rate with public STUN + TURN
