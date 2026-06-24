"""
Healthcare WebRTC Routes
========================
Browser-to-server WebRTC offer endpoint for the healthcare MVP.

Accepts an SDP offer, creates a HealthcareWebRTCSession, and returns an
answer. The caller must supply `session_id` and `phone` query parameters
so the server can correlate the stream with a seeded patient record.

Ref: ADR-024; docs/engineering/goal-vector-healthcare-mvp.md.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.api.healthcare_webrtc_handler import handle_healthcare_offer
from src.domains.healthcare_mvp.domain import HealthcareDomain
from src.infrastructure.azure_openai_client import AzureOpenAILLMClient
from src.infrastructure.logging_config import get_logger

logger = get_logger("api.healthcare.webrtc")

router = APIRouter(prefix="/webrtc", tags=["webrtc"])


class WebRTCOfferRequest(BaseModel):
    sdp: str
    type: str


class WebRTCAnswerResponse(BaseModel):
    sdp: str
    type: str


def _receptionist_factory():
    """Build a fresh HealthcareReceptionist for each call."""
    # Use Azure OpenAI if configured; otherwise raise a clear error so the
    # operator knows the MVP requires LLM credentials.
    llm_client = AzureOpenAILLMClient()
    domain = HealthcareDomain()
    return domain.create_receptionist(llm_client=llm_client)


@router.post("/offer", response_model=WebRTCAnswerResponse)
async def healthcare_webrtc_offer(
    request: Request,
    body: WebRTCOfferRequest,
) -> WebRTCAnswerResponse:
    """
    Accept a WebRTC SDP offer from a browser and return an answer.

    Query parameters:
      - session_id (required): unique call identifier.
      - phone (required): patient phone number; must match a seeded record.
    """
    session_id = request.query_params.get("session_id")
    phone = request.query_params.get("phone")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id query parameter is required")
    if not phone:
        raise HTTPException(status_code=400, detail="phone query parameter is required")

    engine = getattr(request.app.state, "moonshine_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Moonshine WebRTC engine is not enabled or still initializing",
        )

    try:
        answer = await handle_healthcare_offer(
            engine=engine,
            receptionist_factory=_receptionist_factory,
            session_id=session_id,
            offer={"sdp": body.sdp, "type": body.type},
            phone=phone,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("healthcare_webrtc_offer_failed", session_id=session_id, phone=phone, error=str(exc))
        raise HTTPException(status_code=500, detail=f"WebRTC negotiation failed: {exc}") from exc

    return WebRTCAnswerResponse(sdp=answer["sdp"], type=answer["type"])


@router.get("/ice-servers")
async def healthcare_webrtc_ice_servers(request: Request) -> dict:
    """Return ICE server configuration for the browser."""
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
