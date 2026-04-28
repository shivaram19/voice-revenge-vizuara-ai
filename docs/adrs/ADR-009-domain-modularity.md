# ADR-009: Domain-Modular Voice Agent Platform

| Field | Value |
|-------|-------|
| **Date** | 2026-04-27 |
| **Status** | Approved |
| **Scope** | Architecture — Multi-domain plugin system |
| **Research Phase** | BFS (landscape: LiveKit, Pipecat, Vapi domain routing) → DFS (SOLID compliance analysis) → Bidirectional (domain × pipeline interaction) |

---

## Context

The voice agent platform currently serves a single domain: **Construction**. The `ProductionPipeline` hardcodes `ConstructionReceptionist`, construction-specific tools (`FindContractorTool`, `BookAppointmentTool`), construction FAQ seed data, and construction prompts. 

Business requirements now demand support for multiple verticals:
- **Education** — course inquiries, admissions scheduling, fee payment
- **Pharma** — drug information, prescription refill, adverse event reporting
- **Hospitality** — reservation booking, room service, concierge
- **Construction** — existing functionality (contractor lookup, appointment booking)

The hardcoded approach violates the **Open/Closed Principle (OCP)**: adding a new domain requires modifying `production_pipeline.py`, creating a merge bottleneck and regression risk [^94].

---

## Decision

We will adopt a **Domain Plugin Architecture** with the following components:

1. **`DomainPort`** — A new hexagonal port defining the interface every domain must implement.
2. **`DomainRegistry`** — A registry (Strategy Pattern) that maps domain identifiers to domain implementations [^95].
3. **`DomainRouter`** — Routes incoming calls to domains based on called phone number (primary) or URL path (secondary).
4. **`src/domains/{domain_id}/`** — Self-contained domain packages with tools, prompts, seed data, and receptionist factory.
5. **Refactored `ProductionPipeline`** — Injected with `DomainRegistry`; resolves domain per call; never hardcodes a specific domain.

---

## Consequences

### Positive

- **OCP Satisfied**: New domains are added by creating a new package and registering it. Zero changes to pipeline, WebSocket handler, or lifespan.
- **Testability**: Each domain can be unit-tested in isolation with mock `DomainPort` implementations.
- **Operational Flexibility**: Phone numbers can be remapped to different domains via environment variables without redeployment.
- **Team Scaling**: Different teams can own different `src/domains/` packages without merge conflicts in core infrastructure.
- **Research Alignment**: LiveKit's `AgentSession` supports swappable STT/LLM/TTS [^79]; our `DomainPort` extends this pattern to swappable business logic.

### Negative

- **Indirection Cost**: One additional abstraction layer (DomainPort) adds ~50ms to call startup (negligible vs. STT latency).
- **Discovery Overhead**: Engineers must learn the domain package structure before contributing.
- **Shared State Risk**: If domains share a database connection pool, schema migrations must be coordinated.

### Neutral

- **Phone Number Inventory**: Each domain requires at least one Twilio number. Current balance ($16.95) supports this; additional numbers cost $1.15/month.

---

## Alternatives Considered

### Alternative A: Environment-Variable Switch (Single Deploy, Single Domain)

Deploy one container per domain, each with `DOMAIN=education` or `DOMAIN=construction`.

**Rejected**: Higher infrastructure cost (N containers × $30/month ACA). No shared telemetry or centralized routing. Violates DRY — each domain repeats pipeline boilerplate.

### Alternative B: Monolithic Multi-Domain Receptionist

Single `UniversalReceptionist` with a "domain" parameter in every tool and prompt.

**Rejected**: Violates SRP — one class handles all verticals. Prompt context windows bloat as domains accumulate. Tool schemas become ambiguous ("lookup_contact" means contractor in construction, student in education).

### Alternative C: Microservices Per Domain

Each domain is a separate service with its own API.

**Rejected**: Overkill for current scale (10–20 concurrent calls). Network hop between router and domain service adds 50–100ms latency. Operational complexity (N deployments, N health checks) exceeds business value at this stage.

---

## SOLID Validation

| Principle | Before ADR | After ADR |
|-----------|-----------|-----------|
| **S**RP | Pipeline builds receptionist + seeds DB + runs STT/TTS | Pipeline orchestrates only; `DomainPort` builds receptionist |
| **O**CP | Adding domain = editing `production_pipeline.py` | Adding domain = new `src/domains/{id}/` package |
| **L**SP | Only `ConstructionReceptionist` exists | All domains implement `DomainPort`; interchangeable |
| **I**SP | No domain interface | `DomainPort` is minimal (3 methods) |
| **D**IP | Pipeline depends on `ConstructionReceptionist` concrete | Pipeline depends on `DomainPort` abstraction |

---

## Implementation Checklist

- [x] ADR written
- [ ] `DomainPort` added to `interfaces.py`
- [ ] `DomainRegistry` + `DomainRouter` created
- [ ] `src/domains/construction/` migrated from `src/receptionist/`
- [ ] `src/domains/education/` created as reference implementation
- [ ] `ProductionPipeline` refactored for `DomainRegistry` injection
- [ ] `lifespan.py` registers domains
- [ ] `websockets.py` passes `to_number` for routing
- [ ] Integration test: call routed to correct domain

---

## References

[^13]: OpenAI. (2023). Function Calling API Documentation.
[^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
[^28]: Newman, S. (2015). Building Microservices. O'Reilly.
[^42]: Cockburn, A. (2005). Hexagonal Architecture.
[^43]: Twilio. (2024). Media Streams API Documentation.
[^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
[^79]: LiveKit. (2026). Agents Framework. github.com/livekit/agents.
[^94]: Martin, R. C. (2002). Agile Software Development: Principles, Patterns, and Practices. Prentice-Hall.
[^95]: Gamma, E., et al. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
