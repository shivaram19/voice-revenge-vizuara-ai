# ADR-005: AI Receptionist — Capstone Architecture

## Status
**Accepted** — 2026-04-25

## Context
The AI Receptionist answers phone calls, routes callers, handles bookings, takes messages, and answers FAQs. This is a **telephony-first** voice agent, which imposes constraints distinct from browser-based agents:

1. **Transport**: PSTN/SIP → WebSocket audio relay (no WebRTC, no AEC).
2. **Latency floor**: PSTN network overhead adds ~200-500ms [^18].
3. **Barge-in**: Harder without AEC; requires server-side echo suppression or accept degraded interruption handling.
4. **Compliance**: Call recording consent, PCI-DSS for payments, HIPAA for medical.

## Decision
**Build a cascaded pipeline voice agent with Twilio SIP/WebSocket gateway, Distil-Whisper ASR, GPT-4o-mini LLM, Piper TTS, and a 4-tool receptionist suite.**

## Tool Suite

| Tool | Function | Trigger | Latency Budget |
|------|----------|---------|----------------|
| `lookup_contact` | Find employee/department by name/role | "Can I speak to..." | <500ms |
| `check_calendar` | Query availability, book appointment | "I want to book..." | <1s |
| `search_faq` | Retrieve answer from knowledge base | "What are your hours..." | <200ms (cached) |
| `take_message` | Record voicemail, notify recipient | "They're not available" | <200ms |

## Telephony Architecture

```
PSTN Caller ──► Twilio ──► WebSocket ──► Agent Controller ──► Pipeline
                SIP         (mulaw)         (Python/FastAPI)
```

**Audio chain**:
- Input: 8kHz mulaw (PSTN standard) → upsample to 16kHz PCM → STT
- Output: TTS 24kHz PCM → downsample to 8kHz mulaw → Twilio

**Citation**: Twilio Media Streams use WebSocket with 8kHz mulaw [^43].

## Receptionist Personality & Prompt Engineering

**Voice constraints** (per ADR-004 and DFS-05):
- Concise: 10-20 words per response turn.
- Professional but warm: "Good morning, you've reached [Company]. I'm the virtual receptionist."
- Latency masking: "Let me check their calendar..." during tool execution.
- Confirmation before action: "I'll book you for 2 PM with Dr. Chen. Is that correct?"

## Business Hours Logic

**Decision**: Hard-code business hours in config; after-hours mode switches to message-taking only.

**After-hours behavior**:
1. "You've reached [Company]. We're currently closed. Our hours are..."
2. Offer to take a message or schedule a callback.
3. No booking transfers to next business day.

## Fallback Chain

1. **STT failure** (3 consecutive empty transcripts): "I'm having trouble hearing you. Let me transfer you to an operator."
2. **LLM timeout** (>3s): Play pre-recorded "Please hold" audio; retry once.
3. **User requests human** (intent detection): Warm transfer to live operator with context summary.
4. **Abuse/detection**: Play "This call is being recorded for quality purposes" and terminate if profanity detected.

## Data Model

### Call Session
```python
@dataclass
class CallSession:
    session_id: str
    caller_number: str
    called_number: str
    start_time: datetime
    intent: Optional[str] = None
    routed_to: Optional[str] = None
    booking: Optional[Booking] = None
    message: Optional[Message] = None
    recording_url: Optional[str] = None
```

### Booking
```python
@dataclass
class Booking:
    name: str
    phone: str
    service: str
    datetime: datetime
    confirmed: bool = False
```

## Research Provenance
- Twilio. (2024). Media Streams documentation. SIP/WebSocket bridge [^43].
- Chanl.ai. (2026). Production voice agent architecture with telephony gateway [^19].
- Gokuljs. (2026). PSTN latency floor ~500ms [^18].
- Qiu et al. (2026). VoiceAgentRAG for FAQ retrieval [^14].

## Revisit Trigger
Revisit if:
1. Twilio supports native WebRTC for SIP (eliminating mulaw conversion).
2. Real-time accent adaptation improves STT WER by >20% for target demographic.
3. On-device LLM (Llama 3.2 3B) achieves <200ms TTFT on CPU, enabling fully private receptionist.

## References
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^18]: Gokuljs. (2026). Real-time voice agent infrastructure. *gokuljs.com*.
[^18]: Gokuljs. (2026). How Real-Time Voice Agents Work. PSTN overhead analysis.
[^18]: Gokuljs. (2026). Real-time voice agent infrastructure. *gokuljs.com*.
[^19]: Chanl.ai. (2026). Voice Agent Platform Architecture.
[^19]: Chanl.ai. (2026). Voice Agent Platform Architecture.
[^43]: Twilio. (2024). Media Streams API Documentation.
[^43]: Twilio. (2024). Media Streams API Documentation.

[^1]: Gokuljs. (2026). How Real-Time Voice Agents Work. PSTN overhead analysis.
[^2]: Twilio. (2024). Media Streams API Documentation.
[^3]: Chanl.ai. (2026). Voice Agent Platform Architecture.
[^4]: Gokuljs. (2026). Real-time voice agent infrastructure. *gokuljs.com*.
[^5]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
