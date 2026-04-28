# Design Principles: The Ten-Dimensional Filter

This document defines the operating principles that govern every architectural decision in this system. No code is written, no dependency is added, no service is deployed without passing through all ten dimensions.

---

## 1. Research-Driven Decision Making

**Principle**: Every technical decision must cite the specific research paper, RFC, or canonical industry whitepaper that justifies it. This principle is governed by the **Research-First Covenant** (`docs/principles/research-first-covenant.md`), which mandates a three-phase research protocol (BFS → DFS → Bidirectional) before any code is written.

**Application**:
- Before choosing Whisper over wav2vec 2.0, we cite Radford et al. (2022) on weakly supervised scaling to 680,000 hours [^1].
- Before picking WebSockets over gRPC streaming, we cite IETF RFC 6455 and latency benchmarks.
- Before choosing CQRS, we cite Newman (2015) and measured 84% read-performance improvement [^28].
- Before adding any dependency, we complete a TCO analysis with citations [^30].
- Before committing any architectural change, we write an ADR with numbered references [^88].

**The Six Commandments** (see full covenant for elaboration):
1. **No Code Without Citation** — Every claim gets a numbered reference.
2. **Three-Phase Research Protocol** — BFS (landscape) → DFS (validation) → Bidirectional (cross-impact).
3. **ADR-First Rule** — No implementation without a documented Architecture Decision Record.
4. **10-Persona Filter** — Every decision passes through all ten dimensional lenses.
5. **Cost-of-Error Principle** — Front-load research; production fixes cost 100× more [^92].
6. **Reproducibility Guarantee** — Every claim must be reproducible by someone else.

**Anti-pattern**: "Because everyone uses it." "Because it feels faster." "Because the blog post said so." "Because the vendor recommends it." (Marketing is not evidence.)

---

## 2. First-Principles Engineering

**Principle**: Strip away hype and rebuild from axioms.

**Core Axioms Applied**:
| Axiom | Domain | Application |
|-------|--------|-------------|
| Amdahl's Law | Parallelization | ASR batching speedup limit |
| Little's Law | Queueing | `L = λW` — queue depth = arrival rate × wait time |
| CAP Theorem | Distributed systems | Eventual consistency for read models; strong consistency for billing |
| Information Theory | Compression | Opus vs PCM bandwidth trade-offs |
| Dagum's Law | Tail latency | P99 optimization via load shedding |

**Anti-pattern**: "TensorFlow is popular, so we use TensorFlow." (No — we ask: what does our throughput equation predict?)

---

## 3. Distributed Systems at Origin

**Principle**: Design for 1,000,000 concurrent users from Day 0. The architecture that works for 10 users is not merely a smaller version of the architecture for 1M users — it is often a *different* architecture.

**Non-negotiables**:
- Stateless services. Session state belongs to the client or to a dedicated state store.
- Horizontal scaling via event sourcing. No vertical scaling assumptions.
- Backpressure propagation. If TTS is saturated, ASR must know.
- Circuit breakers. If the LLM provider times out, degrade gracefully to cached responses.
- Idempotency keys on every mutating API call.

**Citation**: Brewer (2000) on CAP theorem [^26]; Vogels (2009) on eventual consistency [^27].

---

## 4. Infrastructure-First Observability

**Principle**: The system is only as good as its telemetry. Metrics, traces, logs, and chaos engineering are not afterthoughts — they are architectural requirements.

**RED Metrics** (for every service):
- **R**ate: Requests per second
- **E**rrors: Error rate
- **D**uration: Response time distribution (P50, P95, P99)

**USE Metrics** (for every resource):
- **U**tilization: Percent of resource busy
- **S**aturation: Queue length / work queued
- **E**rrors: Resource error count

**Citation**: Google SRE Book (Beyer et al., 2016) [^29]; Dapper distributed tracing (Sigelman et al., 2010) [^52].

---

## 5. Ethical & Altruistic Design

**Principle**: Build for human flourishing. Privacy, accessibility, and energy efficiency are not features — they are constraints.

**Constraints**:
- Federated learning over central data hoarding where possible.
- On-device inference (Distil-Whisper, Piper TTS) for privacy-critical use cases.
- Voice bias audits using Common Voice dataset [^6].
- Carbon-cost estimation before every GPU cluster decision.

---

## 6. Resource Strategy & TCO

**Principle**: Optimize for Total Cost of Ownership, not just subscription cost.

**Decision Framework**:
```
TCO = Compute + Storage + Network + Operational Overhead + Opportunity Cost
```

**Example**: A GPU instance costs $3/hr but processes 50 concurrent streams. A CPU instance costs $0.50/hr but processes 2 streams. Break-even: GPU is cheaper at >12 concurrent streams. We calculate this before deploying.

**Citation**: Barroso et al. (2018), "The Datacenter as a Computer" [^30].

---

## 7. Diagnostic Rigor

**Principle**: Root-cause analysis over symptom treatment.

**Methodology**:
1. Reproduce with telemetry.
2. Trace the critical path.
3. Identify the tail-at-scale offender (usually not the mean).
4. Fix the root cause; do not add caching to hide it.

**Citation**: Gunawi et al. (2016) on failure analysis in distributed systems [^60].

---

## 8. Curiosity as Duty

**Principle**: The frontier is scanned continuously. Maintain a lab notebook.

**Active Experiments Log**:
| Date | Experiment | Hypothesis | Result | Decision |
|------|-----------|------------|--------|----------|
| 2026-04 | Speculative decoding with Whisper | 2x speedup, identical outputs | Pending | If validated, adopt for production ASR |
| 2026-04 | Mamba state-space for TTS | Faster than Transformer for long sequences | Pending | Evaluate if CMOS > -0.2 |

---

## 9. Clarity Over Cleverness

**Principle**: Every module has a single responsibility and a clear interface. Complexity is the enemy.

**Heuristics**:
- If a function needs more than 3 sentences to explain, it is two functions.
- If an architecture diagram needs a legend with >8 items, it is two diagrams.
- If a dependency has >50 transitive dependencies, question its inclusion.

---

## 10. Inner-Self Alignment

**Principle**: Build what is *right*, not what is *easy*. Long-term maintainability over short-term velocity.

**Questions Before Every Commit**:
- Will I understand this in 6 months without asking anyone?
- If the original author leaves, can a new engineer fix a production bug in <30 minutes?
- Does this abstraction reduce or increase total system entropy?

---

## References
[^1]: Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2022). Robust Speech Recognition via Large-Scale Weak Supervision. *arXiv:2212.04356*.
[^6]: Ardila, R., et al. (2020). Common Voice: A Massively-Multilingual Speech Corpus. *LREC*.
[^26]: Brewer, E. (2000). Towards Robust Distributed Systems. *PODC*.
[^27]: Vogels, W. (2009). Eventually Consistent. *Communications of the ACM*, 52(1), 40-44.
[^28]: Newman, S. (2015). *Building Microservices*. O'Reilly Media. CQRS performance data from: Event-Driven Architectures in Integration as a Service (2024), *IAEME*.
[^29]: Beyer, B., Jones, C., Petoff, J., & Murphy, N. R. (2016). *Site Reliability Engineering*. O'Reilly Media.
[^30]: Barroso, L. A., Clidaras, J., & Hölzle, U. (2018). *The Datacenter as a Computer: Designing Warehouse-Scale Machines*. Morgan & Claypool.
[^52]: Sigelman, B. H., et al. (2010). Dapper, a Large-Scale Distributed Systems Tracing Infrastructure. *Google Technical Report*.
[^60]: Gunawi, H. S., et al. (2016). Why Does the Cloud Stop Computing? *HotCloud*.

[^1]: Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2022). Robust Speech Recognition via Large-Scale Weak Supervision. *arXiv:2212.04356*.
[^2]: Newman, S. (2015). *Building Microservices*. O'Reilly Media. CQRS performance data from: Event-Driven Architectures in Integration as a Service (2024), *IAEME*.
[^3]: Brewer, E. (2000). Towards Robust Distributed Systems. *PODC*.
[^4]: Vogels, W. (2009). Eventually Consistent. *Communications of the ACM*, 52(1), 40-44.
[^5]: Beyer, B., Jones, C., Petoff, J., & Murphy, N. R. (2016). *Site Reliability Engineering*. O'Reilly Media.
[^6]: Sigelman, B. H., et al. (2010). Dapper, a Large-Scale Distributed Systems Tracing Infrastructure. *Google Technical Report*.
[^7]: Ardila, R., et al. (2020). Common Voice: A Massively-Multilingual Speech Corpus. *LREC*.
[^8]: Barroso, L. A., Clidaras, J., & Hölzle, U. (2018). *The Datacenter as a Computer: Designing Warehouse-Scale Machines*. Morgan & Claypool.
[^9]: Gunawi, H. S., et al. (2016). Why Does the Cloud Stop Computing? *HotCloud*.
