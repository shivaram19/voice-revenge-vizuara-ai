"""
FastAPI Application — Composition Root
DIP: This file ONLY wires dependencies. No business logic.
Ref: Hexagonal Architecture (Cockburn 2005) [^42].

Architecture:
    main.py ──► routes.py ──► ConstructionReceptionist (domain)
         │                         │
         ▼                         ▼
    lifespan.py              ToolRegistry (OCP)
         │                         │
         ▼                         ▼
    TwilioGateway            Concrete Tools
    (abstracted)             (contractor, schedule, FAQ)
"""

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Load .env before any other imports that read os.environ.
# Ref: 12-Factor App — config in environment [^88]; OWASP secrets guidance [^89].
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))

from src.api.lifespan import lifespan
from src.api.routes import router as voice_router
from src.api.health import router as health_router
from src.api.metrics import router as metrics_router
from src.api.crm import router as crm_router
from src.api.websockets import handle_twilio_websocket

# Gateway routers
from src.api.gateway.auth import router as gateway_auth_router
from src.api.gateway.tenants import router as gateway_tenants_router
from src.api.gateway.students import router as gateway_students_router
from src.api.gateway.calls import router as gateway_calls_router
from src.api.gateway.analytics import router as gateway_analytics_router
from src.api.gateway.websocket import router as gateway_ws_router

app = FastAPI(
    title="TreloLabs Voice Agent",
    description="AI-powered voice receptionist for business calls — deployed at voice.trelolabs.com",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://voice.trelolabs.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files served under /static for assets
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include API routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(voice_router)
app.include_router(crm_router)

# Gateway routers (frontend integration)
app.include_router(gateway_auth_router)
app.include_router(gateway_tenants_router)
app.include_router(gateway_students_router)
app.include_router(gateway_calls_router)
app.include_router(gateway_analytics_router)
app.include_router(gateway_ws_router)

# WebSocket endpoint
@app.websocket("/ws/twilio/{call_sid}")
async def twilio_websocket(websocket: WebSocket, call_sid: str):
    """Delegate to Twilio Media Streams handler."""
    await handle_twilio_websocket(websocket, call_sid)


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
# [^42]: Cockburn, A. (2005). Hexagonal Architecture.
# [^43]: Twilio. (2024). Media Streams API Documentation.
