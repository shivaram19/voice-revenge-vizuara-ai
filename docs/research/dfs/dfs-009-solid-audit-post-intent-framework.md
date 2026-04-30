# DFS-009: SOLID Audit — Post-Intent-Framework State of the Codebase

> **Date:** 2026-04-30
> **Scope:** Post-remediation SOLID review of `src/` after the work in commits `5b486d1` (best-practice fixes), `67110f9` (Template Method + DI + auto-discovery), and the recent feature deltas (DFS-007 patience, DFS-008 intent framework, ADR-014 voice intent contract).
> **Research Phase:** DFS — depth-dive into structural quality.
> **Status:** Active. Drives the Batch 1-4 refactor sequence in §5.

---

## 1. Why this audit, why now

The codebase has been growing fast through this session: timestamped logs, patience knobs, parent registry, scenario templates, news layer, post-intent state machine, intent-shift switching, per-session budget floor. Each addition was correct in isolation; the question this DFS answers is whether the *aggregate* still respects SOLID — or whether the cumulative weight has eroded the structure that earlier commits worked hard to put in place.

The answer: **the foundations are good, but `production_pipeline.py` has visibly drifted into a god-class, and a small number of SOLID seams need re-tightening before the next round of features lands.** Specifics below, with file:line citations.

The methodology was a deep-scan delegated to an Explore subagent, then spot-verified against `wc -l`, `grep -n`, and direct `Read` on the called-out hot spots.

---

## 2. Verified file-size context

| File | LOC | Comment |
|---|---:|---|
| `src/infrastructure/production_pipeline.py` | **911** | Up from ~600 pre-session. Hot spot. |
| `src/domains/education/receptionist.py` | 446 | Up from ~140 pre-session. Heavy growth from intent-state-machine + intent-shift detection. |
| `src/receptionist/base_receptionist.py` | 258 | Stable, well-factored. |
| `src/infrastructure/interfaces.py` | 214 | Stable. |

The 911-line pipeline file is the headline number; everything in §3 traces back to it.

---

## 3. Top high-severity findings (verified)

### 3.1 [S] HIGH — `production_pipeline.py` is a god-class
**Symptom.** A single class (`ProductionPipeline`, lines 126–878 of `src/infrastructure/production_pipeline.py`) orchestrates: session lifecycle, streaming-STT callbacks, barge-in candidate/confirmation state machine, idle re-prompt timing, LLM filler-during-thinking, turn-length budget adaptation (with floor selection), TTS synthesis + μ-law conversion + chunked sending, emotion-state lookup, latency tracking, log emission, and per-session housekeeping. Twenty-two per-session dicts are tracked on `self`.

**Why it matters.** Each of these subsystems has its own research backing (DFS-007, ADR-013, Communication Accommodation, ITU-T G.168, …). When they cohabit one class, (a) any one of them can introduce a bug that breaks all others, and (b) testability collapses — the only way to test the barge-in logic is to spin up a full pipeline with mocked Deepgram/TTS/LLM.

**Suggested fix.** Carve out three focused collaborators (composition over expansion):

- `BargeInStateMachine(session_id, init_protect_ms, cooldown_ms, min_dur_ms)` — owns `_pending_barge_in_started_at`, `_was_interrupted`, `_last_barge_in_time`, `_handle_barge_in`.
- `TurnBudgetAdapter(session_id, floor, ceiling)` — owns `_caller_word_history`, `_dynamic_max_words`, `_session_budget_floor`; exposes `record_caller_turn()` and `current_budget_for_turn(index)`.
- `AudioSender(stream_sid, send_callback, chunk_size)` — owns `_send_with_tracking`, the chunking + interruptibility logic.

Pipeline becomes the conductor; each collaborator owns one concern. ~250-300 LOC moved out, no behavioural change.

### 3.2 [L] HIGH — `hasattr` introspection where a port should exist
**Symptom.** `production_pipeline.py:280` —
```python
has_record = (
    hasattr(receptionist, "session_has_record")
    and receptionist.session_has_record(session_id)
)
```

I added this myself in commit `2dcfce9`. It's a concrete LSP smell: the pipeline is asking a `Receptionist` for information that the base ABC doesn't promise. Today only `EducationReceptionist` implements it; tomorrow another receptionist will silently fail to expose record-presence and the pipeline will quietly degrade to the no-record floor.

**Why it matters.** The Liskov Substitution Principle says any `Receptionist` should be substitutable for any other without callers having to introspect. `hasattr` is the smell of an unspecified contract.

**Suggested fix.** Add `session_has_record(session_id) -> bool` to the `Receptionist` ABC (`src/receptionist/service.py`) with a default `return False`. Subclasses that have records override; subclasses that don't keep the default. Pipeline drops the `hasattr`.

### 3.3 [D] HIGH — `sys.path.insert` in two production modules
**Symptom.** `src/infrastructure/production_pipeline.py:59` and `src/infrastructure/demo_pipeline.py:53` both call `sys.path.insert(0, str(PROJECT_ROOT))` at module import time.

**Why it matters.** This is path-hacking masquerading as a fix. It works in development but introduces non-determinism in containerised deployments (where the project root is `/app` and is already on `sys.path` via the `WORKDIR`), and it interacts badly with the auto-discovery of domain plugins in `lifespan.py:_discover_domains` because the relative ordering of paths changes.

**Suggested fix.** Delete both lines. Verify the container start-up still succeeds (it should; `Dockerfile.agent` already sets `WORKDIR /app` and copies `src/` to `/app/src/`). Remove the unused `from pathlib import Path` import that becomes orphaned.

### 3.4 [D] HIGH — Education receptionist lazily imports the tenant
**Symptom.** `src/domains/education/receptionist.py:44` —
```python
def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    from src.tenants import get_active_tenant   # <-- lazy import at runtime
    self._tenant = get_active_tenant()
```

Plus a lazy `from src.tenants.jaya_high_school.school_news import render_news_block` at line 374.

**Why it matters.** This violates DIP: the high-level education-domain code reaches into a low-level tenant module to ask *which tenant am I serving?*. Lazy imports were used here to break a circular dependency at runtime; the underlying coupling didn't go away.

**Suggested fix.** Inject the tenant. `EducationDomain.create_receptionist(llm_client, tts_provider, tenant: Optional[Tenant] = None)` — `lifespan.py` already calls `get_active_tenant()` once at startup; pass the result through `DomainPort.create_receptionist`. The lazy `from src.tenants` import disappears, the receptionist becomes test-isolatable (you can inject a `MockTenant`).

### 3.5 [O] HIGH — Tenant registry is hard-coded, not pluggable
**Symptom.** `src/tenants/__init__.py:31-43` —
```python
TENANTS: Dict[str, Tenant] = {
    JAYA_HIGH_SCHOOL.tenant_id: JAYA_HIGH_SCHOOL,
}
def get_active_tenant() -> Optional[Tenant]:
    tenant_id = os.getenv("ACTIVE_TENANT_ID", "jaya-suryapet")
    return TENANTS.get(tenant_id)
```

**Why it matters.** Adding a new tenant (a second school) requires editing this file. The Domain layer (which we extended specifically to be plugin-pluggable in commit `67110f9` — see `_discover_domains` in `lifespan.py`) does this right; the Tenant layer regressed to the pattern Domain *moved away from*.

**Suggested fix.** Mirror the `DomainRegistry` pattern. New `src/tenants/registry.py` with a `TenantRegistry` class; `lifespan.py` auto-discovers tenants like it auto-discovers domains. The hard-coded dict becomes register-on-import, and the `get_active_tenant()` env-var resolution moves into the registry.

---

## 4. Top medium-severity findings (verified)

| # | Principle | Location | Symptom | Fix |
|---|---|---|---|---|
| 4.1 | I | `src/infrastructure/interfaces.py:78–92` (TTSPort) | `synthesize_stream` and `synthesize` co-existing; most adapters override only one | Split into `SyncTTSPort` + `StreamTTSPort` |
| 4.2 | D | `src/api/lifespan.py:63,74,115` | `os.getenv()` calls scattered across orchestration | Centralise in a `PipelineConfig` dataclass loaded once |
| 4.3 | S | `src/domains/education/receptionist.py:32–88` | Constructor initialises 8+ session-state dicts (intent, lingering, pivot, news, shift, …) | Extract `PostIntentStateMachine(session_id)` |
| 4.4 | L | `src/receptionist/base_receptionist.py:247–250` | `_llm_chat_completion` runs sync `LLMPort.chat_completion` in an executor without contract enforcement | Add `async_chat_completion()` to `LLMPort` |
| 4.5 | I | `src/receptionist/service.py:49–72` | Receptionist ABC has 3 abstract methods but the legacy `ReceptionistService` adds 5 unused helpers | Split `CallReceptionist` (3 abstract) + optional `ReceptionistService` mixin |
| 4.6 | O | `src/domains/education/prompts.py` (and siblings) | Each domain has its own `build_<domain>_prompt` function; no registry/factory | `PromptRegistry.get(domain_id).build(context)` |
| 4.7 | D | `src/infrastructure/production_pipeline.py:567–568` | Local `from src.emotion.profile import EmotionalTone` inside `_process_utterance` | Move to module-level import |
| 4.8 | S | `src/domains/education/tools.py` | Tool implementations + course/admission seed data + seed function in one file | Split into `data.py` + `seed.py` + `tools.py` |
| 4.9 | D | `src/domains/router.py:71` | `DomainRouter._load_phone_mapping` reads `DOMAIN_PHONE_MAPPING` env directly | Inject `phone_mapping: Dict[str, str]` from lifespan |
| 4.10 | L/D | `src/domains/education/receptionist.py:290–310` | Mid-call intent switch checks `new_intent_id in self._tenant.scenarios` directly; no null guard if tenant is None | Add `Tenant.get_scenario(intent_id) -> Optional[Scenario]`; receptionist calls it |

---

## 5. Suggested commit-sized refactor batches (priority order)

These are scoped so each batch produces a self-contained commit ≤ ~200 LOC, with no behaviour change visible to callers.

### Batch 1 — Trivial cleanups (≤ 30 LOC)
1. Delete `sys.path.insert` from both pipeline modules (3.3).
2. Add `session_has_record(session_id) -> bool` to `Receptionist` ABC (3.2).
3. Promote the two `_BUDGET_FLOOR_*` constants and `default_domain` literal to documented module-level named constants with inline citations.
**Estimated effort:** 30 minutes. **Risk:** near-zero (compile-time changes only).

### Batch 2 — Centralised configuration (≤ 200 LOC)
1. Create `src/infrastructure/runtime_config.py` with a `RuntimeConfig` dataclass: log level, deepgram key, openai endpoint/key, twilio creds, default domain, active tenant, demo mode, all patience knobs. One `RuntimeConfig.from_env()` factory.
2. Move every `os.getenv()` call out of business modules into `RuntimeConfig`.
3. Pass the config object through `lifespan.py` into `ProductionPipeline`, `DomainRouter`, the new `TenantRegistry`.
**Why before Batch 3:** lots of downstream constructors need DI; centralised config makes the DI ergonomic.
**Estimated effort:** 2 hours. **Risk:** low (mostly mechanical rewrites, but touches enough files that one missed env var would break boot).

### Batch 3 — DIP fix for tenant injection (≤ 150 LOC)
1. Add `tenant: Optional[Tenant]` to `DomainPort.create_receptionist` signature.
2. `lifespan.py` resolves the active tenant via `TenantRegistry` (created in this batch) and passes it into every `domain.create_receptionist(...)`.
3. `EducationReceptionist.__init__` accepts the tenant via DI; the lazy `from src.tenants import get_active_tenant` (and the lazy news-block import) disappear.
**Estimated effort:** 1.5 hours. **Risk:** low; entirely structural.

### Batch 4 — God-class extraction (≤ 300 LOC moved, ~0 added)
1. New `src/infrastructure/barge_in_state.py` with `BargeInStateMachine`. Move 6 dicts + 4 methods.
2. New `src/infrastructure/turn_budget.py` with `TurnBudgetAdapter`. Move 3 dicts + 1 method + the floor constants.
3. `ProductionPipeline` constructs and delegates to the two new collaborators. Total file shrinks from 911 → ~600.
**Estimated effort:** 3-4 hours. **Risk:** medium (most behaviourally impactful refactor; needs the smoke-test scripts from this session re-run before deploy).

### Batch 5 (deferred) — `PostIntentStateMachine` extraction
Splitting the consent-gate / pivot / news / intent-shift bookkeeping out of `EducationReceptionist`. Same shape as Batch 4 but on the receptionist instead of the pipeline. Defer until the post-intent contract has been exercised on more production calls; refactoring while the contract is still stabilising adds churn.

---

## 6. What's clean and worth imitating

These modules exemplify the SOLID patterns we want elsewhere:

- **`src/domains/registry.py` + `src/domains/router.py`** — minimal interfaces, registry pattern, env-driven resolution gated through one well-tested helper. *This is the model Batch 3 is modelled on.*
- **`src/receptionist/base_receptionist.py`** — Template Method done right; subclasses override exactly two abstract methods.
- **`src/tenants/jaya_high_school/tenant.py`** — composition over inheritance; school identity, parent records, scenarios all pluggable members rather than baked-in.
- **`src/infrastructure/interfaces.py`** — typed ports; vendor SDKs cross the boundary at adapters, not at the domain.
- **`src/streaming/streaming_stt_deepgram.py`** — focused class doing one thing (streaming Deepgram WS) with clear callbacks. The pipeline's STT-callback section (lines 366–480) is the *consumer* of this clean module and remains clean *because* the producer is.

---

## 7. Open questions / deferred decisions

1. **Should the `Receptionist` ABC stay async-or-sync mixed?** Section 4.4 raises Liskov tension. A future ADR might mandate `async`-everywhere for receptionists; that's invasive enough to deserve its own decision.
2. **Should `Scenario` be renamed to `IntentSpec`?** ADR-014 §Naming explicitly defers this. Worth revisiting if/when an inbound-call workflow lands and the term "Scenario" becomes ambiguous.
3. **At what call volume should `_BUDGET_FLOOR_*` be re-derived empirically?** DFS-007 §6 already flags this; ≥200 calls before regressing.

---

## References

- Martin, R. C. (2002). *Agile Software Development, Principles, Patterns, and Practices.* Prentice Hall — SOLID principles primary source.
- Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). *Design Patterns* — Template Method, Strategy, Composition.
- Fowler, M. (2018). *Refactoring* (2nd ed.). Addison-Wesley — extraction patterns used in §5 batches.
- ADR-009 — Domain-Modular Voice Agent Platform (the registry/router pattern §6 cites as exemplary).
- ADR-014 — Voice Intent Framework (the scenario contract referenced in §3.5 and §7.2).
- DFS-002 — prior SOLID audit (commit `7e4267a`); this DFS extends rather than supersedes.
