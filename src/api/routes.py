"""
HTTP Routes — REST API Endpoints
SRP: ONLY HTTP routing. No WebSocket, no business logic.
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["voice"])


@router.get("/")
async def root() -> dict:
    """Root endpoint — Twilio status callback target."""
    return {
        "service": "construction-receptionist",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/twilio/inbound")
async def twilio_inbound() -> dict:
    """
    Twilio webhook for inbound calls.
    Returns TwiML to connect call to Media Streams websocket.
    Ref: Twilio (2024). Media Streams API [^43].
    """
    # TODO: Return TwiML <Stream> connect instruction
    return {"status": "connected", "message": "TwiML placeholder"}
