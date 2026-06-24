# DECISION-20260503-002: Auto-Close Silence Tolerance

**Date:** 2026-05-03  
**Proposal:** Increase _AUTO_CLOSE_SILENCE_MS from 3000ms to 8000ms with intent-acknowledgment gate and per-scenario override  
**Risk Level:** Medium  
**Final Decision:** Approved

## Council Deliberation

| Persona | Stance | Key Point |
|---|---|---|
| Research Scientist | Endorse | ADR cites Sacks et al. 1974, Nass & Brave 2005, Hoegen 2019; 8000ms is conservative |
| First-Principles Engineer | Endorse | Commits to data-driven refinement (P95 + 1s); correct epistemic stance |
| Distributed Systems Architect | Endorse | Per-scenario override is right abstraction |
| Infrastructure-First SRE | Endorse | Four metrics and A/B experiment plan specified |
| Diagnostic Problem-Solver | Endorse | "Only after intent acknowledgment" is the key fix |
| Ethical Technologist | Strong Endorse | 3s close was trust violation; 8s respects human processing time |
| Resource Strategist | Endorse | Marginal cost increase but significant trust benefit |
| Curious Explorer | Endorse | A/B test built in; request parent_response_time_ms per turn |
| Clarity-Driven Communicator | Endorse | ADR documents original sin and commits to refinement |
| Inner-Self Guided Builder | Endorse | Patience over efficiency; respect over speed |

## Rationale

Unanimous consensus. Research-backed conservative default with built-in observability and experimental validation. Respects human processing time and conversational structure per Sacks et al. 1974.

## Action Items

- [x] ADR written: `docs/adrs/ADR-022-auto-close-silence-tolerance.md`
- [ ] Code implemented
- [ ] Metrics emitted
- [ ] Decision logged: this file
