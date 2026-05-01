# Voice Revenge Vizuara AI Repository

This workspace now has a clear split between the research-driven voice agent backend and the Slack+CRM-inspired frontend cockpit described in the UX plan.

## Layout
- `backend/`: FastAPI services, infrastructure manifests, scripts, tests, and the research-grade Python toolchain anchored by `pyproject.toml`. Refer to `backend/README.md` for the original mission statement and onboarding commands.
- `frontend/`: Next.js 14 app that implements the Agent Desktop, Pipeline board, Conversation detail, and Supervisor Queue wireframes with static data and design tokens.
- `docs/`, `.github/`, and other top-level directories capture architecture, ADRs, and tooling guidance that span both workstreams.

## Getting started
### Backend
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

The frontend mirrors the interaction-specified flows (live call handling, transcript review, disposition, pipeline transitions, and supervisor visibility) and is ready for iterative data integration once the backend APIs are wired in.
