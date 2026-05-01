# Commit Plan
## Atomic commits grouped by feature accountability

> **Principle:** Each commit owns ONE concern. A reviewer can understand the change by reading the commit message alone. Cross-cutting changes (refactors) are separate from additive changes.

---

## Commit 1: Foundation — SQLite Data Layer for Construction Domain

```
feat(data): add SQLite models for construction receptionist

Adds Contractor, Appointment, CallTask, and TimeSlot entities
with full CRUD operations. SQLite backend eliminates external
database infrastructure for 10-50 concurrent call scale.

Files:
- src/receptionist/models.py
- src/receptionist/construction_seed.py

Refs: [^46] AMA scheduling practices; [^28] microservices data isolation
```

**Why this commit first:** All domain logic depends on these models. They are the bedrock.

---

## Commit 2: Foundation — Conflict-Free Scheduling Engine

```
feat(scheduler): add scheduling engine with business rules

Implements 30-minute slots, 15-minute buffers, daily limits,
and business hours enforcement. Includes voice-formatted output
for natural spoken responses.

Files:
- src/receptionist/scheduler.py

Refs: [^46] AMA optimized scheduling; [^28] Building Microservices
```

**Why separate from models:** Scheduler is a pure logic module. It can evolve independently of storage.

---

## Commit 3: Foundation — Streaming Sentence Aggregator

```
feat(streaming): add sentence buffer for real-time TTS

Buffers streaming LLM tokens into complete sentences before
TTS synthesis. Handles abbreviations, decimals, and barge-in
reset. Reduces perceived latency by 40-60% [^16].

Files:
- src/streaming/sentence_aggregator.py

Refs: [^16] SigArch streaming architecture
```

**Why separate:** Streaming is infrastructure, not domain. Reusable across verticals.

---

## Commit 4: Domain — Abstract Tool Interface + Registry (OCP)

```
feat(tools): add Tool ABC and ToolRegistry for extensible tooling

Open/Closed Principle: new tools register without core changes.
Each tool self-defines its OpenAI schema, execution, and
voice formatting.

Files:
- src/receptionist/tools/base.py

Refs: [^13] OpenAI Function Calling; [^42] Hexagonal Architecture
```

**Why this before concrete tools:** Concrete tools depend on this abstraction. Interface first.

---

## Commit 5: Domain — Construction Contractor Tools

```
feat(tools): add 7 construction-specific tools

Implements: find contractors, check availability, book/cancel/
reschedule appointments, get schedule, schedule outbound calls.
All tools return voice-formatted responses for natural interaction.

Files:
- src/receptionist/tools/contractor_tools.py
- src/receptionist/tools/calendar.py
- src/receptionist/tools/contact_lookup.py
- src/receptionist/tools/faq.py
- src/receptionist/tools/messages.py

Refs: [^13] OpenAI Function Calling API
```

**Why grouped:** These are the concrete implementations of the tool abstraction. They share the same accountability: construction domain logic.

---

## Commit 6: Domain — Outbound Call Queue

```
feat(outbound): add Twilio outbound call task queue

Manages CallTask lifecycle: pending → dialing → connected →
completed/failed. Includes machine detection and status tracking.

Files:
- src/receptionist/outbound_caller.py

Refs: [^41] Twilio REST API; [^41] Twilio Call Status Callbacks
```

**Why separate:** Outbound calling is a distinct capability from inbound reception. Separate failure domain.

---

## Commit 7: Domain — Construction Prompts

```
feat(prompts): add construction-specific system prompt

Emergency triage (3 levels), 8 FAQ categories, tool definitions,
and latency masking fillers. Calibrated for construction caller
psychology: panic → urgency → relief.

Files:
- src/receptionist/prompts/construction_prompt.py
- src/receptionist/prompts/system_prompt.py

Refs: [^16] SigArch streaming; [^12] ReAct reasoning loop
```

**Why separate:** Prompts are content, not code. They change frequently. Isolated for rapid iteration.

---

## Commit 8: Service — Abstract Receptionist Interface (DIP)

```
feat(service): define Receptionist ABC and CallSession

Domain layer depends on abstraction, not implementation.
Defines handle_call_start, handle_transcript, handle_call_end
contract. Preserves backward-compatible ReceptionistService.

Files:
- src/receptionist/service.py

Refs: [^42] Hexagonal Architecture; [^28] Building Microservices
```

**Why before concrete service:** The abstract interface is the contract. Concrete implementations vary by vertical.

---

## Commit 9: Service — Construction Receptionist Implementation

```
feat(service): add ConstructionReceptionist with ToolRegistry

Concrete implementation using ToolRegistry (OCP) and ReAct loop.
Integrates LLM client and TTS provider via dependency injection.
No hardcoded tools — all registered at runtime.

Files:
- src/receptionist/construction_service.py

Refs: [^74] ReAct reasoning; [^13] Function Calling
```

**Why separate from abstract:** The abstract interface is stable. This implementation is vertical-specific and may be cloned for other domains.

---

## Commit 10: Telephony — Abstract Gateway + Twilio Implementation (LSP)

```
feat(telephony): add TelephonyGateway abstraction + Twilio adapter

Liskov Substitution: TwilioGateway implements abstract gateway.
Audio pipeline: 8kHz μ-law ↔ 16kHz PCM ↔ 24kHz PCM.
Provider-agnostic — Plivo/Telnyx adapters can swap in.

Files:
- src/telephony/gateway.py
- src/telephony/twilio_gateway.py

Refs: [^38] ITU-T G.711; [^43] Twilio Media Streams
```

**Why grouped:** Abstract + concrete belong together. The interface is useless without an implementation.

---

## Commit 11: Telephony — Python 3.13 Audio Compatibility

```
fix(audio): add μ-law encode/decode for Python 3.13

audioop removed in Python 3.13 (PEP 594). Implements pure-Python
μ-law companding and linear resampling. Zero dependencies.

Files:
- src/telephony/_audio_compat.py

Refs: [^38] ITU-T G.711
```

**Why separate fix:** This is a compatibility patch, not a feature. Isolated for rollback if needed.

---

## Commit 12: Config — ISP-Compliant Configuration Module

```
feat(config): split monolithic config into focused classes

Interface Segregation: OpenAIConfig, RedisConfig, TwilioConfig,
AppConfig, DeepgramConfig. Clients depend only on config they
use. No more fat AzureConfig with 12 fields.

Files:
- src/config/__init__.py

Refs: [^44] Azure Identity SDK
```

**Why separate:** Configuration is cross-cutting. It should not live inside any single module.

---

## Commit 13: Infrastructure — Deepgram Client Adapter

```
feat(infra): add Deepgram STT/TTS adapter

Implements STTPort and TTSPort using Deepgram Nova-3 (ASR)
and Aura (TTS) via HTTP/WebSocket. No SDK dependency — pure
asyncio + aiohttp. Includes emotion-aware voice selection.

Files:
- src/infrastructure/deepgram_client.py

Refs: [^6] Deepgram Nova-3; Deepgram Aura docs
```

**Why separate from interfaces:** The interfaces are stable. Adapters are replaceable. Deepgram is one of many possible providers.

---

## Commit 14: API — SOLID-Compliant Layer Split (SRP)

```
refactor(api): split main.py into SRP modules

Single Responsibility:
- lifespan.py: startup/shutdown only
- routes.py: HTTP routes only
- websockets.py: WebSocket protocol only
- main.py: composition root only (DIP)

No behavior change. Pure structural refactor.

Files:
- src/api/main.py
- src/api/lifespan.py
- src/api/routes.py
- src/api/websockets.py
- src/api/health.py
- src/api/metrics.py

Refs: [^42] Hexagonal Architecture; [^16] SigArch
```

**Why marked as refactor:** No new features. Existing behavior preserved. Tests pass unchanged.

---

## Commit 15: Conversation — Turn-Taking Engine

```
feat(conversation): add floor management and barge-in detection

Turn-taking engine manages conversational floor states:
IDLE → USER_SPEAKING → AI_SPEAKING → BOTH_SPEAKING.
Implements Sacks-Schegloff-Jefferson turn-transition rules:
300ms pause = relevance place. Respects user silence as
invitation, not just absence of speech.

Files:
- src/conversation/turn_taking.py

Refs: [^16] SigArch; Sacks et al. (1974) turn-taking theory
```

**Why separate from coordinator:** Turn-taking is a self-contained algorithm. It can be tested in isolation.

---

## Commit 16: Conversation — Attentiveness Engine

```
feat(conversation): add emotional intelligence and response timing

AttentivenessEngine detects user emotional state (CALM, RUSHED,
DISTRESSED, CONFUSED) and shapes AI behavior: pause length,
tone, response length, backchannel selection. Core principle:
"Only speak when the user is ready to receive."

Files:
- src/conversation/attentiveness.py

Refs: Goffman (1967) Interaction Ritual; Clark (1996) Using Language
```

**Why separate from turn-taking:** Attentiveness is about emotional intelligence, not floor management. Different accountability.

---

## Commit 17: Conversation — Coordinator

```
feat(conversation): add conversation pipeline orchestrator

Coordinates STT → LLM → TTS with turn-taking and attentiveness
constraints. Handles barge-in cancellation, backchannel injection,
and latency masking. The central nervous system of the voice agent.

Files:
- src/conversation/coordinator.py
- src/conversation/__init__.py

Refs: [^16] SigArch streaming architecture
```

**Why last in conversation series:** The coordinator DEPENDS on turn-taking and attentiveness. It is the integration layer.

---

## Commit 18: Deployment — Construction Bicep + Parameters

```
feat(deploy): add construction-specific Azure Bicep

Simplified infrastructure for 10-50 concurrent calls:
Container Apps (not AKS), Azure OpenAI, Redis, Key Vault,
App Insights. No GPU. No self-hosted STT/TTS. Single container.

Files:
- infrastructure/azure/main-construction.bicep
- infrastructure/azure/parameters.construction.json

Refs: [^44] Azure Well-Architected Framework
```

**Why separate from original Bicep:** Original `main.bicep` is for medical 3-service AKS. Construction Bicep is a different deployment target. Both coexist.

---

## Commit 19: Deployment — Construction K8s Manifests

```
feat(deploy): add construction K8s manifests (single service)

Base + prod overlay for construction receptionist. Single
Deployment, Service, HPA, ConfigMap, Namespace. No STT/TTS
services. Replicas: 3-10. Memory: 512Mi-2Gi.

Files:
- k8s/construction/base/namespace.yaml
- k8s/construction/base/configmap.yaml
- k8s/construction/base/deployment.yaml
- k8s/construction/base/service.yaml
- k8s/construction/base/hpa.yaml
- k8s/construction/overlays/prod/kustomization.yaml
```

**Why separate from base K8s:** Base K8s has 3 services (agent + STT + TTS). Construction K8s is single-service. Different accountability.

---

## Commit 20: Deployment — Construction Deploy Script

```
feat(deploy): add unified construction deployment script

7-phase deployment: prerequisites → build → provision → push →
secrets → deploy → verify. Supports both ACA (recommended) and
AKS targets. Idempotent. Self-documenting.

Files:
- scripts/deploy-construction.sh

Refs: [^44] Azure CLI; [^41] Twilio API
```

**Why separate:** The script is user-facing tooling. It changes independently of infrastructure definitions.

---

## Commit 21: Deployment — Construction Dockerfile

```
feat(deploy): add construction-optimized Dockerfile

Multi-stage build: Python 3.11 slim, non-root user, SQLite volume,
aiohttp for Deepgram. No GPU deps. No STT/TTS services.
Health check on /health/live.

Files:
- docker/Dockerfile.construction
```

**Why separate from Dockerfile.agent:** Agent Dockerfile is generic. Construction Dockerfile is optimized for the construction vertical (single container, SQLite, no GPU).

---

## Commit 22: Documentation — SOLID Compliance Report

```
docs(architecture): add SOLID compliance audit

Documents SRP, OCP, LSP, ISP, DIP violations fixed and the
refactoring approach. Includes file system map showing how
each principle is enforced by directory structure.

Files:
- docs/architecture/solid-compliance.md
```

**Why separate:** Documentation is not code. It can be updated without affecting behavior.

---

## Commit 23: Documentation — Turn-Taking Design

```
docs(architecture): add turn-taking and attentiveness design

Philosophy, anti-patterns, conversation lifecycle, response
shaping matrix, and implementation guide. Core principle:
"Only when you're ready to give attention."

Files:
- docs/architecture/turn-taking-design.md
```

**Why separate from SOLID doc:** Different topic. Different audience (voice engineers vs. software architects).

---

## Commit 24: Documentation — Deepgram Integration

```
docs(integration): add Deepgram Nova-3 + Aura guide

Latency budgets, cost analysis, voice selection, configuration,
fallback strategy, and code examples. Targets 400-600ms round-trip.

Files:
- docs/deepgram-integration.md
```

**Why separate:** Integration docs are reference material. They evolve with API versions.

---

## Commit 25: Documentation — Construction Deployment Guide

```
docs(deployment): add Azure construction deployment guide

Quick start, target comparison (ACA vs AKS), cost estimates,
post-deployment Twilio configuration, monitoring queries,
rollback procedures.

Files:
- docs/deployment-azure-construction.md
```

**Why separate:** Deployment guide is operational. Different from architecture design docs.

---

## Commit 26: Strategy — Caller Personas & Outreach

```
docs(strategy): add construction caller persona research

7 inbound personas, 5 outbound personas, emotional topology
by geography, company-type profiles, objection matrix, and
strategic outreach messaging by segment.

Files:
- docs/strategy/caller-personas-and-outreach.md
```

**Why separate:** Strategy docs are market research. Not engineering. Different review cycle.

---

## Commit 27: Strategy — Supply Chain Geo-SEO

```
docs(strategy): add supply chain geo-SEO landing page strategy

BFS market exploration (8 verticals × 40 sub-segments × 200+
geographies), DFS deep-dive into Memphis 3PL, bi-directional
pain-point-to-capability matching, 60 landing page targets,
seasonal content calendar.

Files:
- docs/strategy/supply-chain-geo-seo-research.md
```

**Why separate from caller personas:** Different market (supply chain vs. construction). Different tactic (SEO vs. direct outreach).

---

## Commit 28: Strategy — Character Ethnography

```
docs(strategy): add immersive supply chain worker profiles

7 deep character studies: owner-operator, broker owner,
warehouse supervisor, cold chain manager, drayage dispatcher,
last-mile driver, maintenance manager. SOLID principles mapped
to human mental models. Ethnographic research method.

Files:
- docs/strategy/character-ethnography-supply-chain.md
```

**Why separate from geo-SEO:** Ethnography is qualitative research. SEO is quantitative tactics. Different methodologies, different audiences.

---

## Commit 29: Tests — Zero-Dependency Test Suite

```
test: add zero-dependency test suite for all modules

9 sentence aggregator tests, 10 receptionist tool tests,
11 scheduler tests. Custom test runner — no pytest dependency.
All tests pass. No mocking required for data layer (SQLite
in-memory).

Files:
- tests/test_runner.py
- tests/test_sentence_aggregator.py
- tests/test_receptionist_tools.py
- tests/test_scheduler.py
```

**Why one commit for all tests:** Tests are cross-cutting. They validate the system as a whole. Grouped because they share the same test runner pattern.

---

## Commit 30: Demo — Construction Scenarios

```
feat(demo): add construction receptionist demo script

6 scenarios: emergency plumbing, kitchen estimate, FAQ lookup,
outbound call scheduling, appointment booking. Uses in-memory
SQLite with 10 seeded contractors.

Files:
- examples/construction_demo.py
- examples/receptionist_demo.py
```

**Why separate:** Demos are user-facing. They validate the integration of all modules. Different accountability from core code.

---

## Commit Order Summary

```
1-3:   Foundation (data, scheduler, streaming)
4-7:   Domain (tools, outbound, prompts)
8-9:   Service (abstract + construction)
10-11: Telephony (gateway + audio fix)
12-13: Infrastructure (config + deepgram)
14:    API refactor (SRP split)
15-17: Conversation (turn-taking + attentiveness + coordinator)
18-21: Deployment (bicep + k8s + script + docker)
22-25: Architecture docs (SOLID + turn-taking + deepgram + deploy)
26-28: Strategy docs (personas + geo-SEO + ethnography)
29:    Tests
30:    Demos
```

---

## Commit Message Template

```
<type>(<scope>): <subject>

<body>

Files:
- <file1>
- <file2>

Refs: <citations>
```

**Types:**
- `feat` — new feature
- `fix` — bug fix
- `refactor` — code change that neither fixes nor adds
- `docs` — documentation only
- `test` — test addition or correction
- `chore` — tooling, build, deps

**Scopes:**
- `data`, `scheduler`, `streaming`, `tools`, `outbound`, `prompts`
- `service`, `telephony`, `config`, `infra`, `api`, `conversation`
- `deploy`, `docs`, `test`, `demo`
