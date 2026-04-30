# ADR-014: Voice Intent Framework — Per-Call Spec + Post-Intent Extension

> **Date:** 2026-04-30
> **Status:** Accepted
> **Drives:** DFS-008
> **Affects:** `src/tenants/<tenant>/scenarios/`, `src/tenants/<tenant>/school_news.py`, `src/domains/education/receptionist.py`, `src/tenants/jaya_high_school/tenant.py`

## Context

The codebase already encodes per-call conversational templates as `Scenario` objects under `src/tenants/<tenant>/scenarios/`. Each scenario has an opening, a closing, a posture note, and success signals. The 2026-04-30 architecture dialogue with the user clarified that this is in fact the project's **canonical Voice Intent contract** — every outbound call binds to exactly one of these specs — and that the contract should be extended with two post-intent offers:

1. **Pivot** (intent-specific, e.g. admission referral after a fee-paid call) — already implemented as `Scenario.post_intent_pivot` (commit 255a437).
2. **News offer** (school-wide, e.g. *"anything else happening at school you'd like to know about?"*) — newly added.

The user's framing: *"voice intent framework specs for every call we make, research-driven template making … after that intent is finished, we'll ask them if anything else they wanna know about anything that's happening in the school."*

DFS-008 establishes the formal Intent contract, the post-intent state machine (pivot → news_offer → close), and the tenant-owned School News layer.

## Decision

1. **Every outbound call binds to exactly one Intent spec.** The existing `Scenario` dataclass IS that contract; renaming is *not* required (Naming note below). Adding new call types means adding new `Scenario` instances, never freeform prompts.

2. **Each tenant ships its own Intent registry.** `src/tenants/<tenant>/scenarios/` is the single source of truth for that tenant's call templates. The generic `EducationDomain` is intent-agnostic; tenants supply intents.

3. **Post-intent extensions are first-class fields.** `Scenario.post_intent_pivot` (intent-specific) and `Scenario.post_intent_news_offer` (school-wide). Both are `Optional` callables — `None` opts out, used wherever cross-asking would damage trust (fee-overdue, attendance-followup).

4. **A deterministic state machine sequences the post-intent offers.** Per-session flags `_intent_satisfied`, `_pivot_offered`, `_news_offered` advance one-shot. At most one offer fires per agent turn, eliminating the "two questions in one turn" anti-pattern.

5. **School news is a tenant-owned data layer.** `src/tenants/<tenant>/school_news.py` carries upcoming events with audience filtering, priority, and `requires_action` flags. Production loads from school CMS/calendar via Redis; dev/test seeds in-process.

6. **All transitions emit structured log events** (`intent_satisfied`, `pivot_offered`, `news_offered`) for post-call analysis and quality scoring.

## Naming

We deliberately keep the existing `Scenario` dataclass name rather than renaming it to `IntentSpec`. Rationale:

- The user's mental model uses "Intent" as a *concept* but the code's `Scenario` type-name is already widely-imported and unambiguous.
- Renaming would require touching ~12 call sites + breaks any external code referencing the type.
- Documentation (DFS-008, this ADR) consistently refers to "Intent" as the concept and `Scenario` as the implementing type. The two are interchangeable in discourse.

If a future ADR introduces a *broader* IntentSpec (e.g. covering inbound calls, internal events, multi-turn workflows), we will reconsider the rename then.

## Consequences

**Positive**
- Every call type is introspectable from one file (`scenarios/<intent_id>.py`).
- New intents (homework follow-up, transport changes, sick-leave check-in, exam-result delivery) drop into the registry with zero core changes.
- Post-intent offers have a deterministic structure → bounded call duration → predictable cost.
- Sensitive scenarios opt out of all extensions → trust-preserving by default.
- Tenant onboarding is reduced to: write `parents.py`, `school_news.py`, scenario files, register Tenant. No core code changes.

**Negative**
- The state machine is per-receptionist-instance memory; a multi-replica deployment with sticky-session load balancing is required (already true; documented in deployment memory).
- Adding a *third* post-intent offer in the future requires extending the state machine logic (current code branches on exactly two flags).
- `success_signals` are simple substring matches; nuanced cases ("yeah I'm wrapping up") may not match. Future LLM-based intent-completion classifier (DFS-008 §7).

**Mitigations**
- The state machine emits enough structured events that a single broken scenario can be diagnosed from one call's log dump.
- Per-tenant Intent registries are independent — a misconfigured Jaya HS scenario cannot affect another tenant.

## Alternatives Considered

1. **Single Mega-Prompt with branching by call type.** Rejected — the LLM cannot reliably branch on a freeform "call type" string the way it can follow a clean opening/closing/posture template, and prompt-engineering the branching point becomes a maintenance hole.
2. **Generative pivot/news offer (no template).** Tempting (let the LLM decide), but produces inconsistent post-intent UX across calls and removes the explicit opt-out for sensitive scenarios. Trust-preserving design wins.
3. **Per-domain (not per-tenant) news layer.** Considered briefly — but each school's calendar is genuinely unique. Tenant-owned is correct.
4. **Combined pivot+news in one offer turn.** Rejected — VUI research [Cohen 2004] shows two-question turns produce 60% information loss in callers >40y. One question per turn is the right unit.

## References

- DFS-008 — Voice Intent Framework
- DFS-007 — Patience-aware conversation thresholds (the `≤18 words/turn` constraint)
- ADR-009 — Domain-modular architecture
- ADR-013 — Patience-aware conversation thresholds
- 2026-04-30 user dialogue: *"voice intent framework specs for every call we make"*
