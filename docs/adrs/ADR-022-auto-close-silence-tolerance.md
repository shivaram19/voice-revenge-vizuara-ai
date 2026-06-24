# ADR-022: Auto-Close Silence Tolerance

**Date:** 2026-05-03  
**Status:** Proposed (under Council deliberation)  
**Scope:** Define silence timeout after the agent delivers substantive content before auto-closing the call  
**Risk Level:** Medium

---

## Context

Call CA2238 (2026-05-03) revealed that `_AUTO_CLOSE_SILENCE_MS = 3000` causes the agent to auto-close 3 seconds after delivering the fee confirmation summary. The parent said "Thank you" 14 seconds after the closing — indicating they were still engaged and processing the information.

The original 3000ms value was set without ADR, without research citation, and without experimental validation. It was derived from intuition ("Suryapet parents speak fast") rather than evidence.

## Decision

Increase `_AUTO_CLOSE_SILENCE_MS` to **8000ms** with the following conditions:

1. **Only fires after intent acknowledgment** — Auto-close only activates after the parent has explicitly acknowledged the primary intent (e.g., said "yes" to fee confirmation). Before acknowledgment, the agent waits indefinitely for a response.
2. **Per-scenario override** — Scenarios can define their own `auto_close_ms`. Default is 8000ms. Sensitive scenarios (fee_overdue_inquiry) may use shorter timeouts.
3. **Experimental validation** — Post-deployment, measure parent response time distribution and adjust to P95 + 1s.

## Consequences

### Positive
- Respects human processing time after substantive information
- Aligns with conversation analysis research on turn-taking
- Reduces premature closure, increasing trust

### Negative
- Increases average call duration by ~5s
- Increases Twilio PSTN cost marginally
- May feel slow to parents who genuinely have nothing to say

### Risks
- **False negative:** Parent is actually disengaged but agent waits 8s before closing
- **Scenario mismatch:** Some scenarios may need shorter tolerance

## Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|---|---|---|---|
| Keep 3000ms | Lower cost | Breaks trust; violates conversation structure | User explicitly reported frustration |
| Remove auto-close entirely | Fully human-like | Infinite hang risk if parent walks away | Production systems need guardrails |
| LLM-driven close detection | Context-aware | Adds 500-1000ms latency; complex | Over-engineered for current stage |
| Variable timeout based on turn length | Theoretically optimal | Complex; no research backing specific formula | Not justified by evidence yet |

## References

- [^CP1]: Sacks, H., Schegloff, E. A., & Jefferson, G. (1974). A Simplest Systematics for the Organization of Turn-Taking for Conversation. *Language*, 50(4), 696–735. — Section 4.2.2 on transition-relevance places and preferred second pair parts.
- Nass, C., & Brave, S. (2005). *Wired for Speech: How Voice Activates and Advances the Human-Computer Relationship*. MIT Press. — Users tolerate 5-10s silence from human-sounding agents.
- Hoegen et al., IVA 2019: Premature closure/interruption reduces trust (p=0.027).
- Call trace: `docs/call-trace-CA2238.md`

## Metrics

- `auto_close_silence_ms_actual` — histogram of actual parent silence before response
- `auto_close_triggered_total` — counter of auto-close events
- `call_duration_ms` — correlation with satisfaction
- Experiment: A/B test 3s vs 8s vs 12s with 30 real parents

## Per-Scenario Overrides

| Scenario | Default | Override | Rationale |
|---|---|---|---|
| fee_paid_confirmation | 8000ms | — | Courtesy call; parent may process slowly |
| fee_partial_reminder | 8000ms | — | Gentle reminder; no urgency |
| fee_overdue_inquiry | 8000ms | 5000ms | Sensitive; parent may be distressed; shorter wait |
| attendance_followup | 8000ms | 6000ms | Institutional; parent may need to check records |
