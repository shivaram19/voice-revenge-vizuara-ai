"""
HTTP Routes — REST API Endpoints
SRP: ONLY HTTP routing. No WebSocket, no business logic.

Research Provenance:
    - Twilio expects TwiML (XML) responses from voice webhooks [^43].
    - TwiML <Connect><Stream> establishes a WebSocket media relay
      for bidirectional 8 kHz μ-law audio [^43].
    - ITU-T G.711 μ-law is the PSTN standard companding algorithm [^38].
    - RFC 6455 defines WebSocket as full-duplex, message-oriented
      transport over TCP [^21].
"""

import os
from pathlib import Path
from urllib.parse import parse_qs
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from datetime import datetime
from typing import Optional

router = APIRouter(tags=["voice"])


@router.get("/", response_class=HTMLResponse)
async def root() -> str:
    """
    Product landing page for voice.trelolabs.com.
    Research: Nielsen & Loranger (2006) found that immediate clarity
    of value proposition increases visitor trust by 33% [^85].
    Single-origin serving avoids CORS preflight on WebSocket upgrades [^21][^84].
    """
    landing_path = Path(__file__).parent / "static" / "index.html"
    if landing_path.exists():
        with open(landing_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<html><body><h1>TreloLabs Voice AI</h1><p>voice.trelolabs.com</p></body></html>"


@router.post("/call")
async def make_outbound_call(
    request: Request,
    to: str,
    language: Optional[str] = "te-IN",
    domain: Optional[str] = "education",
    parent_phone: Optional[str] = None,
) -> JSONResponse:
    """
    Trigger an outbound Twilio call to `to` (E.164 format).
    The TwiML callback pre-seeds language and domain so the agent
    greets in the right language from turn zero.

    Query params:
        to           — E.164 destination, e.g. +919502731467
        language     — BCP-47 code to pre-seed (default: te-IN)
        domain       — domain id for receptionist (default: education)
        parent_phone — override parent_phone custom param if different from `to`
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "")

    if not account_sid or not auth_token or not from_number:
        raise HTTPException(
            status_code=500,
            detail="TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_PHONE_NUMBER not configured.",
        )

    # Build the public TwiML webhook URL
    base_url = str(request.base_url).rstrip("/")
    pp = parent_phone or to
    webhook_url = (
        f"{base_url}/twilio/inbound"
        f"?domain={domain}&language={language}&parent_phone={pp}"
    )

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            to=to,
            from_=from_number,
            url=webhook_url,
            status_callback=f"{base_url}/twilio/status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )
        return JSONResponse({
            "status": "dialing",
            "call_sid": call.sid,
            "to": to,
            "from": from_number,
            "language": language,
            "webhook_url": webhook_url,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/twilio/inbound")
async def twilio_inbound(request: Request) -> Response:
    """
    Twilio webhook for inbound and outbound calls.
    Returns TwiML XML to connect the call to our Media Streams WebSocket.

    The WebSocket relay streams 8 kHz μ-law audio in both directions,
    satisfying the PSTN standard (ITU-T G.711) while allowing the agent
    controller to work with 16 kHz PCM for STT [^38][^43].
    """
    # Twilio POSTs form data including CallSid, From, To, etc.
    # Parse manually — avoids python-multipart dependency in container.
    body_bytes = await request.body()
    form = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(body_bytes.decode("utf-8", errors="replace")).items()}
    call_sid = form.get("CallSid", "unknown")

    # Build absolute WebSocket URL from the incoming request
    base_url = str(request.base_url).rstrip("/")
    # In production behind TLS, force wss://
    # Ref: RFC 6455 §11.1 — WebSocket scheme matches HTTP scheme [^21].
    if base_url.startswith("https://"):
        ws_url = base_url.replace("https://", "wss://", 1) + f"/ws/twilio/{call_sid}"
    else:
        ws_url = base_url.replace("http://", "ws://", 1) + f"/ws/twilio/{call_sid}"

    # Support explicit domain routing via query parameter for outbound calls.
    # Outbound calls initiated via REST API may not include caller/callee
    # metadata in the Media Streams start event, so we pass domain explicitly
    # as a custom parameter [^43].
    query = request.query_params
    domain_param = query.get("domain", "")
    custom_params = f'<Parameter name="direction" value="inbound"/>'
    if domain_param:
        custom_params += f'\n            <Parameter name="domain" value="{domain_param}"/>'

    # No <Say> introduction — the AI greeting is the first audio the caller
    # hears, ensuring a single uniform voice (Deepgram Aura) throughout.
    # A separate Polly voice for the intro was perceived as disjointed
    # (user feedback: "2 woman voices and a man voice").
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            {custom_params}
        </Stream>
    </Connect>
</Response>"""

    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/twilio/status")
async def twilio_status(request: Request) -> dict:
    """
    Twilio call status callback.
    Twilio POSTs here at each status transition (initiated, ringing, answered, completed).
    Returns 200 OK to prevent Twilio warning notifications (ErrorCode 15003) [^43].
    """
    body_bytes = await request.body()
    form = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(body_bytes.decode("utf-8", errors="replace")).items()}
    call_sid = form.get("CallSid", "unknown")
    call_status = form.get("CallStatus", "unknown")
    from src.infrastructure.logging_config import get_logger
    logger = get_logger("api.routes")
    logger.info("twilio_status_callback", call_sid=call_sid, status=call_status)
    return {"status": "received", "call_sid": call_sid, "call_status": call_status}


@router.post("/twilio/recording")
async def twilio_recording(request: Request) -> dict:
    """
    Recording status callback.
    Twilio POSTs here when a recording is ready.
    Ref: Twilio Recordings API [^80].
    """
    body_bytes = await request.body()
    form = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(body_bytes.decode("utf-8", errors="replace")).items()}
    recording_url = form.get("RecordingUrl", "")
    recording_sid = form.get("RecordingSid", "")
    call_sid = form.get("CallSid", "")

    print(f"[RECORDING] Call {call_sid} => {recording_url}")

    # Persist to local log for easy retrieval during demos
    import json, datetime
    log_path = Path(__file__).parent.parent.parent / "recordings" / "recording_log.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "call_sid": call_sid,
            "recording_sid": recording_sid,
            "recording_url": recording_url,
        }) + "\n")

    return {"status": "received", "recording_sid": recording_sid, "call_sid": call_sid}


# References
# [^21]: Fette, I., & Melnikov, A. (2011). RFC 6455: The WebSocket Protocol. IETF.
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation.
# [^43]: Twilio. (2024). Media Streams API Documentation. twilio.com/docs/voice/media-streams.
# [^80]: Twilio. (2024). Recordings API Documentation. twilio.com/docs/voice/api/recording.
# [^84]: Fetch Standard. (2023). CORS protocol. fetch.spec.whatwg.org/#cors-protocol
# [^85]: Nielsen, J., & Loranger, H. (2006). Prioritizing Web Usability. New Riders.
