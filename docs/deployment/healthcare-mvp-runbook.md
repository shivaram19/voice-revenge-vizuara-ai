# Healthcare Patient Follow-Up MVP — Runbook

**Scope:** Standalone voice-agent MVP for hospital post-visit follow-up calls.  
**Date:** 2026-06-24  
**Research Phase:** MVP validation  
**Goal-Engineering Ref:** `docs/engineering/goal-vector-healthcare-mvp.md`

---

## Goal Vector

| Vector | Statement |
|--------|-----------|
| **Objective** | Capture patient well-being, medicine adherence, side effects, and escalation needs after a hospital visit. |
| **Constraint** | Never diagnose or prescribe; escalate emergencies immediately; keep turns short; support Telugu/English code-switching. |
| **Toolset** | Patient lookup, symptom recording, adherence recording, side-effect recording, callback scheduling, escalation, summary persistence. |

---

## Runtime Modes

The MVP ships with two interchangeable transport layers:

1. **WebRTC + Moonshine ASR + ReAct LLM** (`src/api/healthcare_mvp_main.py`)  
   - Self-hosted ASR.  
   - Browser demo at `/static/healthcare-demo.html`.  
   - Uses Azure OpenAI GPT-4o-mini via the existing client.  
   - Tool-calling enabled for structured follow-up records.

2. **Azure VoiceLive / GPT-4.1 real-time** (`scripts/run_healthcare_voicelive.py`)  
   - Native real-time audio model (the engine shared from Microsoft Foundry).  
   - Currently instructions-only; tool-calling integration is the next spike.  
   - Requires `azure-ai-voicelive` preview SDK and working microphone/speakers.

---

## Quick Start — WebRTC Mode

### 1. Environment

```bash
cp .env.example .env
# Edit .env and set:
#   AZURE_OPENAI_ENDPOINT
#   AZURE_OPENAI_KEY
#   AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
# Optional:
#   HEALTHCARE_FOLLOW_UP_LOG=./healthcare_follow_ups.jsonl
```

### 2. Run the server

```bash
python3 -m uvicorn src.api.healthcare_mvp_main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open the browser demo

Navigate to:

```
http://localhost:8000/static/healthcare-demo.html
```

Pick a seeded phone number:

| Phone | Patient | Language |
|-------|---------|----------|
| `+919876543210` | Ramesh Rao | Telugu-English (`te-en`) |
| `+919876543211` | Lakshmi Devi | Telugu (`te`) |
| `+919876543212` | Kiran Kumar | English (`en`) |

Click **Start Microphone & Connect** and speak.

### 4. View dashboard

```bash
curl http://localhost:8000/healthcare/dashboard/patients
curl http://localhost:8000/healthcare/dashboard/patients/P-1001
curl http://localhost:8000/healthcare/dashboard/follow-ups
```

---

## Quick Start — VoiceLive / GPT-4.1 Real-Time Mode

### 1. Install the preview SDK

The `azure-ai-voicelive` package is a preview SDK distributed through Microsoft Foundry. Install it using the method provided by your Foundry project (e.g. a private wheel or index):

```bash
pip install azure-ai-voicelive pyaudio
```

### 2. Environment

```bash
export AZURE_VOICELIVE_API_KEY="..."
export AZURE_VOICELIVE_ENDPOINT="https://<resource>.services.ai.azure.com/"
export AZURE_VOICELIVE_MODEL="gpt-realtime"
export AZURE_VOICELIVE_VOICE="en-US-Ava:DragonHDLatestNeural"
```

### 3. Run

```bash
python scripts/run_healthcare_voicelive.py --phone +919876543210
```

Speak when prompted. Press `Ctrl+C` to exit.

---

## Seeded Data

Patients are loaded from `src/domains/healthcare_mvp/seed.py`.  
Follow-up records are stored in memory and appended to the JSONL log configured by `HEALTHCARE_FOLLOW_UP_LOG`.

---

## Testing

### Unit / integration tests

```bash
python3 -m pytest tests/test_healthcare_mvp/ -v
```

The suite covers:

- Tool execution and shared buffer state
- Prompt construction (goal constraints, patient context, short turns)
- Dashboard serialization and filtering
- Receptionist call flow with a mock LLM
- FastAPI app health and dashboard endpoints

### End-to-end pilot checks (no browser needed)

```bash
python scripts/pilot_healthcare_mvp.py
```

This validates:

1. Health endpoints
2. Dashboard patient lookup and follow-up listing
3. A scripted receptionist conversation (symptom → adherence → side effect → save summary)
4. The saved record appears in the dashboard
5. WebRTC offer endpoint validation errors

To run against a live server:

```bash
python scripts/pilot_healthcare_mvp.py --live --base-url http://localhost:8000
```

---

## Architecture

```
┌─────────────┐     WebRTC      ┌─────────────────────────────┐
│   Browser   │ ◄──────────────►│  src/api/healthcare_mvp_main│
│   demo      │   + DataChannel │  (FastAPI + Moonshine ASR)  │
└─────────────┘                 └──────────────┬──────────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          │                    │                    │
                          ▼                    ▼                    ▼
              ┌──────────────────┐  ┌─────────────────┐  ┌──────────────┐
              │ HealthcareRecept │  │  Azure OpenAI   │  │   Dashboard  │
              │ ionist + Tools   │  │   GPT-4o-mini   │  │   endpoints  │
              └──────────────────┘  └─────────────────┘  └──────────────┘
```

VoiceLive mode bypasses the WebRTC/ReAct stack and connects directly to the Azure real-time endpoint with the same healthcare instructions.

---

## Known Limitations / Next Steps

1. **TTS in WebRTC mode:** Agent responses are sent as text over the DataChannel; the browser uses Web Speech API for playback. Cloud TTS (Sarvam/Deepgram) can be wired in later.
2. **VoiceLive tools:** The current integration uses instructions only. Native function-calling for symptom/adherence recording is the next spike.
3. **Persistence:** In-memory + JSONL. Production needs PostgreSQL/Cosmos DB.
4. **Telugu TTS:** Web Speech API support for Telugu varies by browser. For production, use Sarvam Bulbul v3.

---

## References

- `docs/engineering/goal-vector-healthcare-mvp.md`
- `docs/prompts/hospital-patient-follow-up-prompt.md`
- `src/domains/healthcare_mvp/`
- `src/api/healthcare_mvp_main.py`
- `scripts/run_healthcare_voicelive.py`
