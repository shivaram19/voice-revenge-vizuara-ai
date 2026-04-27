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

from pathlib import Path
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from datetime import datetime

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


@router.post("/twilio/inbound")
async def twilio_inbound(request: Request) -> Response:
    """
    Twilio webhook for inbound calls.
    Returns TwiML XML to connect the call to our Media Streams WebSocket.

    The WebSocket relay streams 8 kHz μ-law audio in both directions,
    satisfying the PSTN standard (ITU-T G.711) while allowing the agent
    controller to work with 16 kHz PCM for STT [^38][^43].
    """
    # Build absolute WebSocket URL from the incoming request
    base_url = str(request.base_url).rstrip("/")
    # In production behind TLS, force wss://
    # Ref: RFC 6455 §11.1 — WebSocket scheme matches HTTP scheme [^21].
    if base_url.startswith("https://"):
        ws_url = base_url.replace("https://", "wss://", 1) + "/ws/twilio/inbound"
    else:
        ws_url = base_url.replace("http://", "ws://", 1) + "/ws/twilio/inbound"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling TreloLabs Voice AI. Connecting you to our virtual receptionist.</Say>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="direction" value="inbound"/>
        </Stream>
    </Connect>
</Response>"""

    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/twilio/recording")
async def twilio_recording(request: Request) -> dict:
    """
    Recording status callback.
    Twilio POSTs here when a recording is ready.
    Ref: Twilio Recordings API [^80].
    """
    form = await request.form()
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
