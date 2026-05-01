# ADR-014: Backend Gateway for Frontend Integration

## Status
Accepted — 2026-05-01

## Context

The `feat/refactor` branch contains a production-grade voice agent backend (FastAPI, Twilio, Deepgram, Azure OpenAI) and a new Next.js 14 frontend dashboard. The frontend currently runs entirely on mock data. We need a stable API contract between frontend and backend that:

1. Serves dashboard data (students, call history, analytics)
2. Observes live voice calls in real-time
3. Provides auth endpoints compatible with the frontend's current mock-auth contract
4. Persists education-domain entities without disrupting the voice pipeline

## Decision

We will build a **dedicated gateway module** (`backend/src/api/gateway/`) that coexists with the existing voice API. The gateway has its own SQLite database for education-domain persistence, an in-memory call-state manager for real-time observation, and a set of REST + WebSocket endpoints under `/gateway/v1/*`.

### Why a separate gateway module instead of extending CRM scaffold?

- **Single Responsibility**: The voice API (`/call`, `/twilio/*`) handles telephony webhooks and bidirectional audio. The gateway handles dashboard data and frontend sessions. Mixing them would couple unrelated concerns.
- **Stability**: The voice pipeline is latency-sensitive. Gateway DB queries must not block telephony threads.
- **Evolution**: The gateway can later be extracted into a separate service (API Gateway pattern) without touching voice code.

### Why SQLite for the gateway database?

- Zero infrastructure — aligns with the existing SQLite usage in `receptionist/models.py`
- Demo-ready — no PostgreSQL or connection pooling required for school-scale deployments
- Migration path — schema is simple enough to port to PostgreSQL later with SQLAlchemy or similar

### Why in-memory `CallStateManager` instead of Redis?

- The expected observer count is < 10 (school staff dashboard)
- `asyncio.Queue` per WebSocket client is sufficient for broadcast
- Redis would add operational complexity; we can add it later if horizontal scaling is needed

## Consequences

### Positive
- Frontend can immediately consume real data without Supabase setup
- Voice pipeline remains untouched — zero regression risk for telephony
- Call transcripts are persisted for audit and analytics
- Gateway auth mirrors mock-auth shape, enabling smooth Supabase migration later

### Negative
- SQLite is not horizontally scalable — gateway DB lives on a single node
- In-memory call state is lost on process restart (acceptable for MVP; calls in flight are still handled by Twilio)
- Mock auth is not production-grade — must be replaced with OAuth2/JWT before public launch

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|-----------------|
| Extend `/api/v1/crm/*` scaffold | Would mix dashboard and voice concerns; CRM scaffold has no persistence layer |
| Use Supabase for all gateway data | Requires Supabase project provisioning; blocks immediate development |
| Add gateway tables to `receptionist.db` | Would couple education domain to construction-domain schema |
| Redis for call state | Adds container/infra overhead; not needed for < 10 concurrent observers |

## Implementation

- `backend/src/api/gateway/db.py` — SQLite schema + CRUD for students, call_logs, transcripts, tenants, users
- `backend/src/api/gateway/models.py` — Pydantic request/response schemas
- `backend/src/api/gateway/auth.py` — Login/logout/session endpoints
- `backend/src/api/gateway/students.py` — CRUD + search
- `backend/src/api/gateway/calls.py` — Call history + active calls
- `backend/src/api/gateway/analytics.py` — Dashboard KPIs + system status
- `backend/src/api/gateway/websocket.py` — `/ws/gateway/calls` for real-time observation
- `backend/src/infrastructure/call_state.py` — In-memory singleton tracking active calls

## Pipeline Instrumentation

The voice pipeline (`websockets.py` and `production_pipeline.py`) emits events to `CallStateManager`:

1. **Call Start** (`websockets.py` `start` event) → `CallStateManager.register_call()`
2. **Transcript** (`production_pipeline.py` `_on_transcript()`) → `CallStateManager.append_transcript()` + persist to `transcripts` table
3. **Call End** (`websockets.py` `stop` event) → `CallStateManager.finalize_call()` + persist to `call_logs` table

The frontend WebSocket iterates over active calls and streams transcript events.

## References
- ADR-009 (Domain-Modular Architecture)
- ADR-013 (Patience Thresholds)
- Cockburn, A. (2005). Hexagonal Architecture.
- FastAPI WebSocket documentation (fastapi.tiangolo.com/advanced/websockets/)
