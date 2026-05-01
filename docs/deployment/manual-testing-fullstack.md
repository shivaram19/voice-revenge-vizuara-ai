# Fullstack Manual Testing Guide

Date: 2026-04-30  
Scope: Local backend + Next.js frontend scaffold verification  
Research Phase: Implementation Validation  

## 1) Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Git Bash or PowerShell
- Optional for call flows: Twilio account and public tunnel (for example, ngrok)

## 2) Backend Setup (FastAPI)

1. From repo root:
   - `python -m venv .venv`
   - Windows: `.venv\Scripts\activate`
2. Install dependencies:
   - `pip install -e .`
3. Configure environment:
   - copy `.env.example` to `.env`
   - set minimum required keys (or run in demo mode):
     - `DEMO_MODE=true`
4. Start backend:
   - `uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload`

## 3) Frontend Setup (Next.js)

1. Open another terminal:
   - `cd landing`
2. Install dependencies:
   - `npm install`
3. Configure frontend env:
   - copy `landing/.env.local.example` to `landing/.env.local`
4. Start frontend:
   - `npm run dev`
5. Open:
   - `http://localhost:3000`

## 4) API Smoke Checks

Run these in a terminal while backend is running:

- `curl http://127.0.0.1:8000/health/live`
- `curl http://127.0.0.1:8000/health/ready`
- `curl http://127.0.0.1:8000/api/v1/crm/summary`
- `curl http://127.0.0.1:8000/api/v1/crm/interactions`
- `curl http://127.0.0.1:8000/api/v1/crm/transcript/VC-201`

Expected:
- All endpoints return JSON with HTTP 200.
- `/api/v1/crm/*` returns scaffold CRM payloads.

## 5) Frontend Manual Test Cases

### Case A: App boots and renders
- Open `http://localhost:3000`
- Verify Voice CRM workspace is visible.
- Verify left navigation shows: Home, Live, Pipeline, Contacts, Automations, Analytics.

### Case B: Backend data wiring
- Keep backend running.
- Refresh page.
- Verify KPI cards render values from `/api/v1/crm/summary`.
- Verify active interactions list is populated from `/api/v1/crm/interactions`.

### Case C: Transcript fetch on selection
- Click a different interaction row.
- Verify transcript panel updates (API request to `/api/v1/crm/transcript/{interactionId}`).

### Case D: Backend failure fallback
- Stop backend.
- Refresh frontend.
- Verify UI still renders local scaffold data.
- Verify warning banner appears indicating API unavailable.

### Case E: Navigation behavior
- Click through each view in left rail.
- Verify center/right panes remain functional and layout does not break.
- Verify compact/comfortable density toggle updates row spacing.

## 6) Voice Flow Manual Checks (Optional Twilio)

1. Expose local backend publicly (example with ngrok):
   - `ngrok http 8000`
2. Set Twilio webhook to:
   - `POST https://<your-ngrok-domain>/twilio/inbound`
3. Place a call to Twilio number.
4. Verify:
   - Twilio receives valid TwiML response.
   - WebSocket upgrade path `/ws/twilio/{call_sid}` is hit.
   - Status callback `/twilio/status` receives lifecycle events.

## 7) Common Failure Patterns

- Frontend shows API unavailable:
  - check backend is on `127.0.0.1:8000`
  - check `NEXT_PUBLIC_BACKEND_URL` in `landing/.env.local`
- `ModuleNotFoundError` on backend:
  - ensure virtualenv is active
  - rerun `pip install -e .`
- Twilio call fails:
  - confirm valid public URL
  - verify `.env` contains Twilio credentials

## 8) Exit Criteria

Manual validation passes when:
- Backend health endpoints are green.
- CRM API endpoints return expected scaffold payloads.
- Next.js UI fetches backend data successfully.
- Frontend fallback behavior is graceful when backend is down.

## References

[^1]: FastAPI Documentation. (2026). *Lifespan and Application Structure*. https://fastapi.tiangolo.com/  
[^2]: Next.js Documentation. (2026). *App Router and Data Fetching*. https://nextjs.org/docs  
[^3]: Twilio Documentation. (2026). *Programmable Voice Media Streams*. https://www.twilio.com/docs/voice/media-streams
