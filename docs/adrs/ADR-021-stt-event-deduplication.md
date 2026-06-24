# ADR-021: STT Event Deduplication

**Date:** 2026-05-03  
**Status:** Proposed (under Council deliberation)  
**Scope:** Prevent duplicate pipeline actions when Deepgram emits multiple `speech_final` events for the same utterance  
**Risk Level:** High

---

## Context

Call CA2238 (2026-05-03) revealed a critical bug: Deepgram's streaming STT emitted two `speech_final` events for the parent's "Hello?" utterance within 54ms. The first event triggered the cached consent dispatch. The second event, because `_final_buffers` was repopulated by a concurrent `is_final` event, fell through to the LLM fallback path and regenerated the same consent line. The parent heard "Is this a good time to talk to you, sir?" twice.

This violates:
- User trust (repetition feels robotic)
- The Research-First Covenant (assumed `speech_final` uniqueness without evidence)
- Hoegen et al., IVA 2019: style-matching and non-repetition increase trust (p=0.027)

## Decision

Implement a **two-layer defense**:

1. **Deduplication window:** 200ms timestamp-based guard for identical transcripts
2. **Buffer state flag:** Suppress `is_final` appends after `speech_final` until new utterance starts

## Consequences

### Positive
- Eliminates duplicate pipeline actions
- Preserves cache-hit latency (<50ms)
- STT-agnostic (works with Deepgram, Whisper, AssemblyAI)

### Negative
- 200ms window may delay processing of legitimate rapid-fire utterances
- Requires per-session state tracking
- Adds complexity to the already-complex `_on_transcript` method

### Risks
- **False positive:** Two different utterances within 200ms could be incorrectly deduplicated
- **STT behavior change:** Future Deepgram updates may alter duplicate patterns

## Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|---|---|---|---|
| Increase endpointing_ms to 800ms | Reduces duplicate rate at source | Increases response latency; doesn't guarantee uniqueness | Treats symptom, not root cause |
| Deduplicate on exact text hash only | Simple | Misses near-duplicate rephrasings; no time bound | Too broad |
| LLM-driven turn classifier instead of keyword matching | No keyword false positives | Adds 500-1000ms latency per turn | Violates cache-hit latency requirement |
| Ignore duplicates and let LLM handle gracefully | No code change | Parent hears repetition; breaks trust | Violates ethical and user requirements |

## References

- [^CP1]: Sacks, H., Schegloff, E. A., & Jefferson, G. (1974). A Simplest Systematics for the Organization of Turn-Taking for Conversation. *Language*, 50(4), 696–735.
- Hoegen et al., IVA 2019: Style-matching increases trust (p=0.027)
- Deepgram (2024). Streaming API Documentation: Endpointing and SpeechFinal events
- Call trace: `docs/call-trace-CA2238.md`

## Metrics

- `stt_duplicate_events_total` — counter of deduplicated events
- `stt_duplicate_rate` — gauge: duplicates / total speech_final events
- Alert threshold: `stt_duplicate_rate > 5%` for 5 minutes
