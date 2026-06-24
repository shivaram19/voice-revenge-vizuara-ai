"""
WebRTC Routes — Browser-to-Server Real-Time ASR
================================================
Provides a single POST endpoint that accepts a WebRTC SDP offer from a
browser and returns an SDP answer, establishing a peer connection that
streams audio to the self-hosted Moonshine v2 ASR engine.

Ref: ADR-024 (WebRTC Transport for Self-Hosted ASR)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.api.webrtc_handler import handle_offer
from src.infrastructure.logging_config import get_logger

logger = get_logger("api.webrtc.routes")

router = APIRouter(prefix="/webrtc", tags=["webrtc"])


class WebRTCOfferRequest(BaseModel):
    sdp: str
    type: str


class WebRTCAnswerResponse(BaseModel):
    sdp: str
    type: str


@router.post("/offer", response_model=WebRTCAnswerResponse)
async def webrtc_offer(
    request: Request,
    body: WebRTCOfferRequest,
) -> WebRTCAnswerResponse:
    """
    Accept a WebRTC SDP offer from a browser and return an answer.

    The caller must supply a `session_id` query parameter so the server can
    correlate the peer connection with the ASR stream and transcript channel.
    """
    session_id = request.query_params.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id query parameter is required")

    engine = getattr(request.app.state, "moonshine_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Moonshine WebRTC engine is not enabled or still initializing",
        )

    try:
        answer = await handle_offer(
            engine=engine,
            session_id=session_id,
            offer={"sdp": body.sdp, "type": body.type},
        )
    except Exception as exc:
        logger.error("webrtc_offer_failed", session_id=session_id, error=str(exc))
        raise HTTPException(status_code=500, detail=f"WebRTC negotiation failed: {exc}") from exc

    return WebRTCAnswerResponse(sdp=answer["sdp"], type=answer["type"])


@router.get("/ice-servers")
async def webrtc_ice_servers(request: Request) -> dict:
    """
    Return ICE server configuration for the browser.

    In production this should include TURN credentials from environment
    variables to traverse symmetric NATs. The default returns a public
    Google STUN server for local development only.
    """
    import os

    ice_servers = [{"urls": "stun:stun.l.google.com:19302"}]

    turn_url = os.getenv("TURN_SERVER_URL", "").strip()
    turn_user = os.getenv("TURN_SERVER_USERNAME", "").strip()
    turn_cred = os.getenv("TURN_SERVER_CREDENTIAL", "").strip()

    if turn_url and turn_user and turn_cred:
        ice_servers.append(
            {
                "urls": turn_url,
                "username": turn_user,
                "credential": turn_cred,
            }
        )

    return {"iceServers": ice_servers}
