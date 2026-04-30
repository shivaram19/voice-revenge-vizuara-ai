# Goals and Research Plan

> **Status:** Living document. Refreshed when goals advance or new research opens.
> **Owners:** Architecture + Research (this repo's two hats).
> **Methodology:** AGENTS.md → Research-First Covenant → Decompose → BFS → DFS → Bidirectional → ADR → Code.
> **Date:** 2026-04-30.

---

## 1. Product goal (one sentence)

**Ship a production voice agent that calls parents at Jaya High School, Suryapet about school fees with the same patience, dignity, and accuracy a thoughtful school administrator would — at a cost and reliability that lets us onboard the next 50 tier-3 Indian schools without re-architecting.**

Success is measured by:

| Metric | Target | How measured |
|---|---|---|
| Parent satisfaction (post-call SMS poll) | ≥ 4.2 / 5 | Twilio SMS poll after each call |
| Primary-intent completion rate | ≥ 90 % | Detected via `success_signals` matched in transcripts |
| Per-call cost (full stack) | ≤ ₹6 | Twilio + Deepgram + Azure OpenAI + Container App |
| End-to-end p50 / p95 latency | ≤ 800 ms / ≤ 1500 ms | OTel `voice.latency.ms` histogram |
| Tenant onboarding time (new school) | ≤ 1 day | parents.py + school_news.py + scenarios/ + Redis seed |

These are *outcomes*, not features. Features serve them.

---

## 2. Engineering goal (one sentence)

**Keep the codebase research-first, SOLID-clean, observable, multi-tenant, and 1M-concurrent-ready — and prove every claim with a citation per AGENTS.md §Research-First Covenant.**

| Discipline | Concrete proof we're holding it |
|---|---|
| Research-first | Every numeric default in code traces to a Tier-1 source in a DFS doc |
| SOLID | DFS-009's 5 high-severity findings closed; per-call regressions caught by CI |
| Observable | Every conversation event timestamped + `t_ms_since_call_start` reachable in Log Analytics |
| Multi-tenant | New tenant = `src/tenants/<slug>/` + Redis seed, zero core code changes |
| 1M-ready | Stateless Container App; Redis for hot data; OTel sampling 1.0 for compliance |

---

## 3. Cultural goal (one sentence)

**Build what we'd want our own parents to receive on a phone call about money for their child's school.**

Operationalised as:

- Default after intent satisfaction is **close warmly** (consent-gated, DFS-008 §3).
- Sensitive scenarios (`fee_overdue_inquiry`, `attendance_followup`) MUST opt out of pivot/news offers (ADR-014 §1.3).
- Every patience knob (DFS-007) is calibrated for *Suryapet parents specifically*, not Silicon-Valley defaults.
- 10-Persona Filter (AGENTS.md) applies to every change.

---

## 4. The 10-persona filter, condensed

Every PR / commit / change must pass these — recorded by the commit message, not in a checklist file:

1. **Research Scientist** — citation provided or `[CITATION NEEDED]` flagged.
2. **First-Principles Engineer** — derived from primitives, not industry trends.
3. **Distributed Systems Architect** — survives a 1M-user thought experiment.
4. **Infrastructure-First SRE** — emits structured events with timestamps.
5. **Ethical Technologist** — dignifies the parent on the line.
6. **Resource Strategist** — TCO impact known.
7. **Diagnostic Problem-Solver** — root cause, not symptom.
8. **Curious Explorer** — failure modes documented.
9. **Clarity-Driven Communicator** — ADR for any architectural choice.
10. **Inner-Self Guided Builder** — would I want this for my parent?

---

## 5. Where the work stands today

**Live in production (revision 39 on `trelolabs-prod-app`):**

- Outbound calls to two seeded test parents (`+918919230290` Mr. Shiv Ram, `+919491116789` Mrs. Lakshmi Devi).
- Voice Intent Framework (ADR-014): 5 scenarios (paid_confirmation, partial_reminder, overdue_inquiry, admission_inquiry, attendance_followup) with sensitivity-aware pivot/news matrix.
- Patience-aware turn-taking (DFS-007 / ADR-013): env-driven endpointing, barge-in, filler, idle re-prompt, max-turn-words.
- Communication Accommodation (DFS-007 §6): adaptive turn-budget mirroring the caller's word count, with a per-session floor of 6 (with record) or 12 (no record).
- Consent-gated post-intent offers (DFS-008 §3): pivot/news fire only on explicit invitation; default is close.
- Mid-call intent switching: keyword-based detection of "admission", "absent" routes the rest of the call into the matching scenario.
- Timestamped structured logs reaching Log Analytics with `t_ms_since_call_start` per event.

**Acknowledged debt (DFS-009):**

- 5 high-severity SOLID findings, 10 medium.
- `production_pipeline.py` at 911 LOC; needs decomposition into `BargeInStateMachine` / `TurnBudgetAdapter` / `AudioSender`.
- `hasattr` introspection where a port should live.
- Lazy imports masking circular dependencies.
- Tenant layer regressed from registry pattern; needs `TenantRegistry`.
- Empirical numbers (patience knobs, post-intent acceptance) marked `[CITATION NEEDED]` until ≥200 production calls give us our own telemetry.

---

## 6. Research plan — open questions, by phase

### BFS (landscape — what else is out there?)
- **B-1.** Tenant data ingest: Redis vs. Cosmos vs. event-stream-from-SIS — TCO + latency comparison.
- **B-2.** Inbound-call transport: Twilio Voice vs. Plivo vs. Exotel for India PSTN — latency + cost + DLT compliance.
- **B-3.** Indian-name STT: Deepgram Nova-3 vs. Sarvam vs. AI4Bharat IndicConformer — WER on parent-name corpus.

### DFS (vertical depth — does the candidate hold up?)
- **D-1.** *DFS-010: Telugu code-switching prosody.* When and how to render Telugu in Aura TTS without sounding stilted. Tied to the language_preference field already on `ParentRecord`.
- **D-2.** *DFS-011: LLM-based intent-satisfaction classifier.* Replace the keyword-based `success_signals` matcher with a tiny classifier; cite Allen 1997 DAMSL precedents.
- **D-3.** *DFS-012: Empirical patience-knob calibration.* After ≥200 production calls, regress completion-rate against actual EOU pause distributions; revisit DFS-007 numerics.
- **D-4.** *DFS-013: Post-call quality scoring.* Define + cite a quality metric (turn count, success_signal latency, parent abandonment, satisfaction-poll response) reproducible from logs.

### Bidirectional (cross-domain impact)
- **X-1.** Patience profile × telephony codec. Does G.711 μ-law on Twilio bias the EOU distribution we measure? Cross-cite ITU-T G.168.
- **X-2.** Parent record schema × GDPR / India DPDP Act. Audit `ParentRecord` against the 2023 DPDP Act before a real school's data lands in Redis.

### ADRs queued (decisions waiting on research)
- **ADR-015 — Redis-backed parent record port.** Hexagonal port + adapter; ingestion job; TTL strategy; consistency with school SIS. Blocked on B-1.
- **ADR-016 — Inbound call workflow.** A different posture from outbound; receptionist-as-listener; routing by called number. Blocked on B-2.
- **ADR-017 — DPDP-compliant data retention.** Recording lifecycle, transcript redaction, parent right-to-erasure. Blocked on X-2.
- **ADR-018 — Tenant onboarding playbook.** Operational doc for adding the 2nd school. Depends on Batch 3 of DFS-009 landing.

---

## 7. Refactor plan (engineering debt — DFS-009)

The five batches in DFS-009 §5 are the engineering hygiene track. Order is locked:

1. **Batch 1** — sys.path delete + `session_has_record` ABC + named constants (~30 LOC, 30 min).
2. **Batch 2** — RuntimeConfig dataclass; centralise env reads.
3. **Batch 3** — Tenant injection via DomainPort + TenantRegistry.
4. **Batch 4** — God-class extraction from `production_pipeline.py`.
5. **Batch 5** — `PostIntentStateMachine` extraction (deferred until contract stabilises).

Refactors do NOT advance product goals on their own; they're the cost of *not* slowing down later. Each batch's own commit message will cite the DFS-009 finding it closes.

---

## 8. Done-criteria for this plan

This plan is "done" when one or more of the following triggers fire:

- A first non-Jaya school onboards (ADR-018 lands).
- We hit ≥1,000 production calls and refresh the empirical numbers (DFS-012 lands).
- The audit hash recomputes (re-run DFS-009) and finds no high-severity SOLID violations.
- A new product direction emerges (e.g., outbound → bidirectional inbound) that requires a new charter.

Until then: every commit cites the goal it serves; every doc cites its source.

---

## References (this charter, not the work it points at)

- `AGENTS.md` — Project Operating Instructions, v1.1 (2026-04-27).
- `docs/principles/research-first-covenant.md` — Research-First Covenant.
- `docs/principles/design-principles.md` — 10-Persona Filter source.
- `docs/research/dfs/dfs-007-patience-thresholds-jaya-suryapet.md` — patience methodology.
- `docs/research/dfs/dfs-008-voice-intent-framework.md` — intent contract.
- `docs/research/dfs/dfs-009-solid-audit-post-intent-framework.md` — current debt.
- `docs/adrs/ADR-009-domain-modularity.md` / `ADR-013` / `ADR-014` — landed decisions.
