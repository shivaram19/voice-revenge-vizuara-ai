# ADR-001: Transport Protocol for Client-Server Audio

## Status
**Accepted** — 2026-04-25

## Context
The voice agent requires full-duplex audio streaming between client (browser/mobile) and server. Three protocols were evaluated: WebSocket, WebRTC, and raw TCP/RTP.

## Decision
**Use WebRTC for client-facing audio transport, with WebSocket for signaling and gRPC for internal service communication.**

## Consequences

### Positive
- **Sub-300ms media latency achievable** via UDP and selective forwarding.
- **Built-in AEC enables barge-in**, a core product requirement.
- **Browser-native** — no plugins or native app required.
- **SFU architecture scales horizontally** without transcoding overhead.

### Negative
- **Increased complexity**: ICE, STUN, TURN, DTLS-SRTP negotiation.
- **Firewall traversal**: ~10-15% of users need TURN relay, adding cost.
- **Observability is harder**: Encrypted media prevents server-side inspection.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| WebSocket-only | TCP head-of-line blocking; no AEC; barge-in nearly impossible |
| gRPC to browser | Requires gRPC-Web proxy; poor browser audio API integration |
| Raw UDP/RTP | Must implement congestion control, packet loss concealment from scratch |

## Research Provenance
- LiveKit (2026): "WebRTC achieves ~150ms latency with lower network/CPU consumption and near-zero jitter, while WebSocket exhibits ~200ms" [^17].
- UGent thesis (2023): SFU forwarding is "far cheaper than transcoding, so a single server can handle many more participants" [^55].
- RFC 8830 (WebRTC): Mandatory encryption and congestion control.

## Revisit Trigger
Revisit if:
1. Native speech-to-speech models (GPT-4o realtime) become cost-competitive, eliminating need for client-side streaming.
2. WebTransport (HTTP/3) achieves maturity with better browser support.

## References
[^17]: LiveKit. (2026). Why WebRTC beats WebSockets for realtime voice AI.
[^17]: LiveKit. (2026). Why WebRTC beats WebSockets for realtime voice AI.
[^55]: Van Landuyt, D. (2023). Comparative Study of WebRTC Architectures. *Ghent University*.
[^55]: Van Landuyt, D. (2023). Comparative Study of WebRTC Architectures. *Ghent University*.

[^1]: LiveKit. (2026). Why WebRTC beats WebSockets for realtime voice AI.
[^2]: Van Landuyt, D. (2023). Comparative Study of WebRTC Architectures. *Ghent University*.
