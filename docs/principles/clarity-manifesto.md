# Clarity Manifesto: Zero Ambiguity Protocol

> **There is no "maybe" in clarity-driven engineering.**

---

## The Rule

Every sentence in this repository must commit. Hedging is a bug. Vagueness is technical debt.

### Banned Words & Phrases

The following words are **prohibited** in ADRs, architecture docs, and design specifications:

| Banned | Replacement |
|--------|-------------|
| maybe | decide yes/no and document why |
| perhaps | state the fact or mark as unknown |
| could | state what **will** happen or what the system **does** |
| might | same as above |
| possibly | remove or replace with probability + evidence |
| likely | replace with measured probability or definitive statement |
| probably | same as above |
| consider | either do it or don't; "evaluated and rejected" is acceptable |
| optional | either required or removed |
| may | use "will" (system behavior) or "must" (requirement) |
| suggest | state the decision |
| recommend | state the decision |
| should | use "must" (requirement) or "will" (design choice) |
| would | use "does" or "will" |

### Exceptions

1. **Research papers quoted verbatim** — the original author's hedging is preserved in citation blocks.
2. **Uncertainty Register** — hypotheses are explicitly tracked with confidence scores and evidence gaps.
3. **Risk sections in ADRs** — risks are stated definitively: "X will fail under condition Y."

---

## Clarity Levels

| Level | Standard | Example |
|-------|----------|---------|
| **L0: Definitive** | System behavior | "The Agent Controller aborts TTS within 50ms of barge-in detection." |
| **L1: Conditional** | Explicit condition + outcome | "If GPU utilization exceeds 95% for 60s, HPA adds one node." |
| **L2: Probabilistic** | Measured probability only | "Cache hit rate is 75% ± 5% under evaluated load." |
| **L3: Unknown** | Explicitly marked | "[UNKNOWN] Semantic VAD latency under 10k concurrent streams." |

**Rule**: L3 items must have an assigned owner and a deadline for resolution.

---

## Application to Existing Work

Every document in this repository must pass the clarity linter:

```bash
grep -riE '\b(maybe|perhaps|could|might|possibly|likely|probably|consider|optional|may|suggest|recommend|should|would)\b' docs/
```

**Result must be empty** for a document to be marked FINAL.

---

## Why This Matters

Ambiguous language creates:
1. **Decision paralysis** — engineers wait for "more clarity" that never arrives.
2. **Implementation drift** — "consider using Redis" becomes "maybe we use Redis" becomes "someone used Redis somewhere."
3. **Review churn** — PRs bounce back and forth because the spec was never committed.

Definitive language creates:
1. **Fast execution** — engineers know exactly what to build.
2. **Clear accountability** — the ADR author owns the decision.
3. **Measurable outcomes** — "will" becomes "did" in post-hoc analysis.

---

*This manifesto is itself definitive. It does not suggest clarity. It mandates it.*
