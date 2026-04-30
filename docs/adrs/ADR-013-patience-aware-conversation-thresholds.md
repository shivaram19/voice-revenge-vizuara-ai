# ADR-013: Patience-Aware Conversation Thresholds Driven by Caller Demographics

> **Date:** 2026-04-30  
> **Status:** Accepted  
> **Drives:** DFS-007  
> **Affects:** `src/infrastructure/production_pipeline.py`, `src/streaming/streaming_stt_deepgram.py`, `src/infrastructure/logging_config.py`, deployment env vars

## Context

The platform's conversation-timing parameters (end-of-utterance silence, barge-in cooldown, initial AEC protection) were inherited from English-language voice-agent vendor defaults (Deepgram, ElevenLabs, LiveKit). DFS-007 establishes that those defaults are *systematically wrong* for our deployed audience — Telugu-speaking parents in Suryapet, Telangana — and produce premature endpoint detection, missed backchannels treated as interrupts, and frustrating "you stopped on me" failures.

The fix is not to globally lower or raise a number; it is to make every patience-relevant threshold a **first-class deployment parameter** so each cohort can be tuned to its actual demographic.

## Decision

1. **Every patience-relevant threshold is read from environment variables with research-backed defaults**, never hard-coded as a module-level constant. The defaults are the DFS-007 numbers calibrated for Suryapet parents; deployments to other cohorts override them via env.
2. **Adaptive backchannel discrimination.** Add a minimum-duration gate (`BARGE_IN_MIN_DURATION_MS`, default 400 ms) so short continuers ("haan", "hmm") do not trigger barge-in.
3. **Filler-during-thinking.** When LLM latency exceeds `LLM_FILLER_AFTER_MS` (default 1500 ms) and no audio has been emitted yet for the turn, send a brief filler ("One moment, please") to avoid silence ambiguity.
4. **Idle re-prompt.** When no caller speech is detected for `IDLE_REPROMPT_MS` (default 6000 ms) and the agent is not speaking, send a gentle re-prompt ("Please take your time, I am listening").
5. **Maximum agent turn length.** Trim/split LLM responses exceeding `MAX_AGENT_TURN_WORDS` (default 18) into multiple shorter turns.
6. **Every conversation event is logged with a high-resolution timestamp and `t_ms_since_call_start`.** Logs become the source of truth for tuning numbers 1–5 against real call data.

## Numeric Defaults (DFS-007)

| Env Var | Default | Industry baseline | Source |
|---|---:|---:|---|
| `STT_ENDPOINTING_MS` | 400 | 200 | Yates 1973, Crystal 2003 |
| `STT_UTTERANCE_END_MS` | 1800 | 1000 | Tannen 2005 |
| `BARGE_IN_INITIAL_PROTECTION_MS` | 800 | 500 | ITU-T G.168 |
| `BARGE_IN_COOLDOWN_MS` | 1500 | 1000 | Heldner & Edlund 2010 |
| `BARGE_IN_MIN_DURATION_MS` | 400 | n/a | Heldner & Edlund 2010 |
| `LLM_FILLER_AFTER_MS` | 1500 | n/a | Frontiers 2024, Wang 2025 |
| `IDLE_REPROMPT_MS` | 6000 | n/a | Frontiers 2024 |
| `MAX_AGENT_TURN_WORDS` | 18 | n/a | DFS-007 §3.2 priyaṃ vada |
| `DEFAULT_DOMAIN` | `education` | (was `construction`) | Use-case alignment |

## Consequences

**Positive**
- Tunable per cohort without code change or rebuild.
- Patience parameters become observable and auditable.
- Numbers are traceable back to peer-reviewed sources via DFS-007.
- Telemetry-driven re-tuning loop becomes possible.

**Negative**
- Slightly longer end-to-end calls (≈+5 to +15% duration) due to higher endpointing/utterance-end thresholds.
- Slightly higher TTS spend per call (more filler, more re-prompts).
- New env vars to manage in deployment configuration; risk of misconfiguration.

**Mitigations**
- Calibration metrics emitted for every call: `patience.endpointing_used_ms`, `patience.barge_in_count`, `patience.idle_reprompt_count`, `patience.filler_emitted`.
- Dashboard alarm if any cohort's `patience.barge_in_false_positive_rate` exceeds 5%.

## Alternatives Considered

1. **Global hard-coded constants tuned for Suryapet.** Rejected — fragile, requires rebuild per cohort, can't A/B test.
2. **ML-based adaptive endpointing per call.** Strong long-term option but premature; we need calibration data first. Captured as future work in DFS-007 §6.
3. **Single "patience profile" enum (`urban` / `rural` / `elderly`).** Lower flexibility than independent env vars; coarser tuning. Re-evaluate after 1000 calls of empirical data.

## References

- DFS-007 — Patience-aware conversation thresholds for Suryapet parents
- ADR-009 — Domain-modular architecture (this ADR composes on top)
- ADR-012 — OpenTelemetry instrumentation control (logging foundation)
- All DFS-007 references are inherited.
