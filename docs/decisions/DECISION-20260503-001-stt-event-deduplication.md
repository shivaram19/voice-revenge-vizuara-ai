# DECISION-20260503-001: STT Event Deduplication

**Date:** 2026-05-03  
**Proposal:** Add two-layer STT deduplication per ADR-021  
**Risk Level:** High  
**Final Decision:** Approved

## Council Deliberation

| Persona | Stance | Key Point |
|---|---|---|
| Research Scientist | Endorse | ADR cites Deepgram docs and Hoegen 2019; request 100-call validation post-deployment |
| First-Principles Engineer | Endorse | Two-layer defense is axiomatically sound; neither layer alone is sufficient |
| Distributed Systems Architect | Concern | Key should normalize case; punctuation differences may slip through |
| Infrastructure-First SRE | Endorse | Metrics and alerts specified in ADR |
| Diagnostic Problem-Solver | Endorse | Root cause addressed; request unit test with mock duplicate events |
| Ethical Technologist | Endorse | Eliminates repetition that breaks trust per Hoegen 2019 |
| Resource Strategist | Endorse | ~10 lines of code; negligible runtime cost |
| Curious Explorer | Concern | Propose A/B test post-deployment; not blocking |
| Clarity-Driven Communicator | Endorse | ADR exists; commit should reference ADR-021 and CA2238 |
| Inner-Self Guided Builder | Endorse | Serves user's deeper need for human-like agent |

## Rationale

Two-layer defense is sound, addresses root cause, includes observability, and serves user trust. All concerns are addressable (case normalization, metrics pipeline, unit test, A/B experiment). No blocking concerns.

## Action Items

- [x] ADR written: `docs/adrs/ADR-021-stt-event-deduplication.md`
- [ ] Code implemented
- [ ] Unit test added
- [ ] Metrics emitted
- [ ] Decision logged: this file
