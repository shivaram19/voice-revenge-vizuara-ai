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

from fastapi import FastAPI, WebSocket

from src.api.lifespan import lifespan
from src.api.routes import router as voice_router
from src.api.health import router as health_router
from src.api.metrics import router as metrics_router
from src.api.websockets import handle_twilio_websocket

app = FastAPI(
    title="Construction Receptionist",
    description="AI Receptionist for building trades — Azure-deployed",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(voice_router)

# WebSocket endpoint
@app.websocket("/ws/twilio/{call_sid}")
async def twilio_websocket(websocket: WebSocket, call_sid: str):
    """Delegate to WebSocket handler."""
    await handle_twilio_websocket(websocket, call_sid)


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
# [^42]: Cockburn, A. (2005). Hexagonal Architecture.
# [^43]: Twilio. (2024). Media Streams API Documentation.
