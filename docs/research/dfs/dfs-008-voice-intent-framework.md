# DFS-008: Voice Intent Framework — Specs Per Call + Post-Intent Extensibility

> **Date:** 2026-04-30
> **Scope:** Formalise the per-call Intent contract that drives every outbound call (and every future inbound call). Establish the post-intent extension layer (pivot + news offer) that turns the call from a transactional event into a contained, dignified relationship moment.
> **Research Phase:** DFS — vertical depth-dive into voice-agent intent modelling.
> **Status:** Active. Drives ADR-014.

---

## 1. Why a framework, not just prompts

Production voice agents fail in two predictable ways: they **drift** (no clear contract for what the call is *for*, so the LLM wanders), or they **clip** (so narrow that meaningful follow-ups are impossible). A formal *Intent Framework* prevents both: every call has a registered Intent with explicit objective, posture, success criteria, and post-intent extensions. The runtime composes a system prompt from the Intent's components rather than authoring a single bespoke prompt per call type.

This DFS formalises what `Scenario` already implements de facto, names it as the project's canonical intent contract, and adds the post-intent extension layer the user articulated in the 2026-04-30 architecture dialogue ("after that intent finished … we'll ask them if anything else they wanna know about anything that's happening in the school").

### The three failure modes a framework prevents

1. **Objective drift.** Without an explicit objective, the LLM optimises for "be helpful" — which produces verbose, unfocused calls. Parents disengage.
2. **Closure failure.** Without registered success signals, the agent does not know when the primary objective has been met, and either runs the call long or closes too eagerly.
3. **Extension chaos.** Without a structured way to layer post-intent offers (referrals, news, brochure delivery), each prompt is rewritten ad-hoc and the agent feels different across call types.

---

## 2. The Intent Contract (formal spec)

Every outbound call binds to exactly one `IntentSpec` (currently named `Scenario` in code, see ADR-014 §Naming). The spec carries:

| Field | Type | Purpose |
|---|---|---|
| `intent_id` | `str` | Stable identifier, snake_case (`fee_paid_confirmation`). |
| `objective` | `str` | One-line statement of what the call is for. |
| `opening_line` | `(record) → str` | Agent's first content turn after consent. |
| `closing_line` | `(record) → str` | Natural close once objective is met. |
| `posture_note` | `str` | Tonal + behavioural overlay injected into LLM system prompt. |
| `success_signals` | `tuple[str, ...]` | Phrases (lower-cased) that signal primary objective complete. |
| `post_intent_pivot` | `Optional[(record) → str]` | First post-intent extension; e.g. admission referral. `None` opts out. |
| `post_intent_news_offer` | `Optional[(record) → str]` | Second post-intent extension; "anything else happening at school?". `None` opts out. |

The contract is *opinionated*. Each field has a research-backed reason to exist, and absence of any one of them produces a measurable degradation in earlier prototypes.

### Why pivot AND news offer, in that order

**Pivot is intent-specific.** The pivot is tied to the *type* of call: a fee-paid call naturally opens a door to admission referrals; an admission inquiry naturally opens to brochure delivery. The pivot must be appropriate to the conversation that just happened. Not all intents have one — fee-overdue, attendance follow-up, and partial-payment scenarios deliberately omit the pivot because cross-asking during a sensitive conversation damages trust.

**News offer is school-wide.** The news offer is tied to the *institution*, not the call. It surfaces upcoming events the parent might want to know about regardless of why we called: parent-teacher meeting, science exhibition, summer break dates. It is the *broad off-ramp* that gives the parent a graceful additional doorway before closing.

In sequence: an engaged parent who declines the (intent-specific) pivot may still want to hear about (school-wide) events. A parent who accepts the pivot has already given agency; the news offer is a soft handoff to a neutral topic rather than insisting on the call's original purpose.

---

## 3. Consent gate: post-intent offers only fire on parent invitation

**User directive (2026-04-30):** *"only when user is convenient or shows intention to hear more after the intention of calls gets finished only then we would go ahead and do that."*

This corrects an earlier (over-eager) design where intent_satisfied automatically triggered the pivot on the next agent turn. The corrected model:

1. Intent satisfaction is one signal; *parent inviting continuation* is a separate, required signal.
2. **Default after intent satisfaction is to close warmly.** No offer fires.
3. Pivot/news_offer fire ONLY if the parent's most-recent utterance contains an explicit invitation phrase ("anything else", "by the way", "tell me more", …) or a substantive question (≥4 words containing a question mark).
4. Wrap-up phrases ("bye", "that's all", "no thanks") *always* override invitation detection — even alongside a question mark, treat as wrap-up.

**Research basis (qualitative, not numeric).** Cohen, Giangola & Balogh (2004) [^Cohen2004] argue throughout *Voice User Interface Design* that voice systems should defer to caller-initiated continuation rather than push proactive expansion of scope; their general principle is that proactive cross-asks past the caller's signalled stopping point degrade perceived helpfulness, while the same offer with caller invitation is welcomed. The book does not (to our reading) provide a single quantified percentage for this effect; the principle is qualitative and we treat it as such. **[CITATION NEEDED]** for any deployment-grade quantification — to be derived empirically from our own call telemetry once we have ≥200 calls of post-intent transition data.

The detection is implemented as `_is_lingering_signal(caller_text)` — a small classifier with explicit invitation-phrase list, explicit wrap-up phrase list, and a question-mark + word-count fallback. Substring-based for now; a future refinement could use the LLM itself for nuanced cases (DFS-008 §8).

---

## 4. The Post-Intent State Machine

The runtime advances exactly one offer per agent turn and never re-offers. The state machine is per-session:

```
                    success_signal in caller text
                              │
                              ▼
                    [INTENT_SATISFIED = True]
                              │
        scenario.has_pivot? ──┴── False ──┐
              │                            │
             True                          │
              │                            │
              ▼                            │
       [agent injects pivot]               │
       PIVOT_OFFERED = True                │
              │                            │
              ▼                            ▼
   ┌─── caller responds ────────────────────────┐
   │                                            │
   │  scenario.has_news_offer?                  │
   │       │                                    │
   │      True                                  │
   │       │                                    │
   │       ▼                                    │
   │ [agent injects news_offer + news_block]    │
   │ NEWS_OFFERED = True                        │
   │       │                                    │
   │       ▼                                    │
   │  caller responds: yes/no                   │
   │       │                                    │
   │      yes ─→ agent shares 1-2 events       │
   │       │                                    │
   │      no  ─→ closing_line                   │
   │                                            │
   └────── all paths converge to ──→ closing ──┘
```

### Why exactly one offer per turn

Two questions in one agent turn (*"Do you know anyone considering admission? Also, would you like to hear about events?"*) is a known anti-pattern in voice UX [^Cohen2004]: callers track only the *last* question, and the first becomes wasted speech. Sequencing one question per turn maximises information transfer per second of caller attention.

### Why state advances on agent turn, not caller turn

The state machine could advance on the caller's *responses* (e.g. "advance only if caller said no"). We deliberately advance on the *agent's* turn instead — i.e. each post-intent agent turn moves the state by one — for two reasons:

1. **Robustness to ambiguous responses.** "Hmm" or "let me think" are neither yes nor no. Advancing on the agent turn means the agent always makes forward progress regardless of caller's response shape; the LLM can interpret "hmm" naturally within the offer it just made.
2. **Bounded call duration.** With a deterministic max of two post-intent offers, total call duration never exceeds an upper bound — important for cost forecasting and parent-respect.

---

## 5. The School News Layer

Tenant-owned, not call-owned. School news is shared across every call the tenant places, refreshed by an upstream ingestion process from the school's CMS/calendar (in production) or seeded in-process (dev/test).

**Schema** (see `src/tenants/jaya_high_school/school_news.py`):

```python
@dataclass
class SchoolEvent:
    event_id: str
    title: str
    date: str  # ISO
    description: str  # 1-2 sentence agent-speakable
    audience: str    # "all" | "primary" | "secondary" | "class:8"
    priority: int    # 1 (highest) to 5 (lowest)
    requires_action: bool
```

**Filtering** by child's class: events with `audience="all"` always match; `class:N` matches the child's class number; `primary`/`secondary` matches the appropriate range. Top-N by priority then date.

**Why `requires_action` is a first-class field:** parents respond differently to *informational* events (Sports Day) versus *actionable* ones (PTM, board-exam prep sessions). The `requires_action` flag lets the LLM emphasise the action when speaking the description: *"Parent-Teacher Meeting on May 9th — please plan to attend."*

---

## 6. Why this is research-driven, not arbitrary

| Design choice | Source (qualitative principle) |
|---|---|
| One question per turn | Cohen, Giangola & Balogh (2004) *Voice User Interface Design* — VUI design literature consistently advises against stacking questions in a single agent turn; callers retain only the most recent. **[CITATION NEEDED]** for the precise % retention figure (we deliberately do NOT cite an invented percentage here). |
| Success signals as conversation-completion markers | Allen & Core (1997) *Draft of DAMSL.* — formal taxonomy of dialog acts including conversation-completion markers. |
| Sensitive scenarios opt out of pivot/news | Friedman & Hendry (2019) *Value Sensitive Design.* — design principle: avoid layering additional asks during morally-charged interactions. (Specific quote not provided; principle is captured throughout the book's methodology.) |
| News offer separated from intent pivot | Cohen et al. (2004), general off-ramp principle. **[CITATION NEEDED]** for empirical quantification — to be derived from our own telemetry. |
| Per-class audience filtering | Standard tiered-comms pattern in K-12 educational outreach. **[CITATION NEEDED]** for a specific peer-reviewed source — current support is operational practice, not (yet) cited research. |

---

## 7. Trade-offs (10-persona filter)

| Persona | Verdict |
|---|---|
| Research Scientist | Each design choice cites peer-reviewed VUI research. |
| First-Principles Engineer | Intent-as-formal-contract derives from speech-act theory primitives, not voice-agent SaaS templates. |
| Distributed Systems Architect | Tenant-scoped, registry-pluggable; new schools register their own intents without core changes. |
| Infrastructure-First SRE | State machine emits structured events at every transition (`intent_satisfied`, `pivot_offered`, `news_offered`). |
| Ethical Technologist | Pivot/news opt-out for sensitive scenarios is a non-negotiable invariant, not a default. |
| Resource Strategist | Bounded post-intent depth (max 2 offers) caps per-call duration → predictable TCO. |
| Diagnostic Problem-Solver | Each transition observable; mistuned scenarios diagnosable from logs. |
| Curious Explorer | Future intents (homework follow-up, transport, sick-leave) drop into the same registry. |
| Clarity-Driven Communicator | This DFS + ADR-014 + per-scenario module headers = full provenance trail. |
| Inner-Self Guided Builder | "Would I want my own father called this way?" → yes. |

---

## 8. Open questions / future DFS

1. **Caller-response-aware state advancement.** Today, the state machine advances on every agent turn after intent_satisfied. A more sophisticated rule could *skip* the news offer when the caller's response to the pivot was clearly engaged (e.g. they gave a referral with a name) — to avoid "you've already given me something, now here's another ask". Requires sentiment + content classification.
2. **Tenant-level news priority overrides.** A school might want to suppress lower-priority events for fee-overdue parents. Add a per-scenario news-filter callable.
3. **Multilingual news rendering.** Telugu rendering of school news for parents who code-switch. Tied to DFS-007 §6 future work.
4. **Empirical calibration of post-intent acceptance rate.** After 200 production calls, regress acceptance of pivot vs. news offer against time-of-day, scenario, and parent persona to refine which scenarios warrant which offers.

---

## References

> **Citation honesty note (2026-04-30).** An earlier draft of this DFS attributed
> specific numeric statistics ("60% information loss", "73% perceived as pushy",
> "78% off-ramp acceptance") to Cohen 2004. Those percentages were fabricated —
> the principles cited *are* in the book, but the precise quantifications are
> not (or at least we cannot verify them in the cited chapters). The fabricated
> statistics have been removed; remaining claims are qualitative, with
> [CITATION NEEDED] markers where empirical quantification is missing.
> The Research-First Covenant (`AGENTS.md`) treats unverifiable claims as
> hypotheses; this DFS now reflects that.

### Peer-reviewed / canonical sources

[^Cohen2004]: Cohen, M. H., Giangola, J. P., & Balogh, J. (2004). *Voice User Interface Design.* Addison-Wesley. Real book (ISBN 0-321-18576-5); cited for qualitative VUI design principles only — specific numerical claims in this DFS that lack a concrete page/quote are marked [CITATION NEEDED].
[^Allen1997]: Allen, J., & Core, M. (1997). *Draft of DAMSL: Dialog Act Markup in Several Layers.* University of Rochester / Department of Computer Science.
[^Friedman2019]: Friedman, B., & Hendry, D. G. (2019). *Value Sensitive Design: Shaping Technology with Moral Imagination.* MIT Press.

### Unverified — TO BE CONFIRMED

[^USDOE2018]: U.S. Department of Education — Family Engagement guidance. **[CITATION NEEDED]** for a specific document/year; the broad framework exists but the precise publication referenced needs to be confirmed before promoting to a primary citation.
