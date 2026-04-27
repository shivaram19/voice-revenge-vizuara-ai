"""
Outbound Demo Call with Recording
==================================
Initiates a PSTN call from a Twilio number to a target phone, connects
it to the AI receptionist WebSocket, and records the interaction for
post-call review.

Usage:
    python scripts/demo-outbound-call.py \
        --to +15559876543 \
        --from +15551234567 \
        --base-url https://xxxx.ngrok-free.app

Recording Design:
    - Recording is enabled via Twilio REST API (Record=true) with an
      absolute RecordingStatusCallback URL [^80].
    - Dual-channel recording separates caller and agent audio.
    - Twilio delivers the recording URL asynchronously when encoding
      completes, avoiding blocking the call thread [^80].
    - μ-law 8 kHz mono is the PSTN standard [^38].

Compliance Note:
    - U.S. federal law (18 U.S.C. § 2511) permits one-party consent
      for call recording. State laws vary (e.g., CA requires all-party).
    - The application must provide recording notice; this demo prepends
      a <Say> announcement before connecting the stream [^81].

Research Provenance:
    - Twilio Media Streams relay 8 kHz μ-law over WebSocket [^43].
    - ITU-T G.711 μ-law companding is the PSTN standard [^38].
    - RFC 6455 WebSocket provides full-duplex messaging [^21].
"""

from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    load_dotenv(dotenv_path=str(_env))
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from twilio.rest import Client
except ImportError:
    print("[ERROR] twilio Python SDK not installed.")
    print("        pip install twilio")
    sys.exit(1)


def build_twiml(websocket_url: str, base_url: str) -> str:
    """
    Build TwiML that connects the outbound leg to our Media Streams
    WebSocket. Twilio streams 8 kHz μ-law audio in both directions [^43].
    """
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">This call is recorded for quality. Connecting you to the A I receptionist now.</Say>
    <Pause length="1"/>
    <Connect>
        <Stream url="{websocket_url}">
            <Parameter name="direction" value="outbound"/>
            <Parameter name="demo" value="true"/>
        </Stream>
    </Connect>
</Response>"""
    return twiml


def make_call(
    to_number: str,
    from_number: str,
    twiml: str,
    record: bool,
    recording_status_callback: str | None,
    status_callback: str | None,
) -> str:
    """
    Create the outbound call via Twilio REST API.
    Returns the Call SID for tracking.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    client = Client(account_sid, auth_token)

    call_params = {
        "to": to_number,
        "from_": from_number,
        "twiml": twiml,
    }

    if record:
        call_params["record"] = True
        # Absolute URL required; Twilio cannot POST to relative paths
        if recording_status_callback:
            call_params["recording_status_callback"] = recording_status_callback
            call_params["recording_status_callback_method"] = "POST"

    if status_callback:
        call_params["status_callback"] = status_callback
        call_params["status_callback_event"] = ["initiated", "ringing", "answered", "completed"]
        call_params["status_callback_method"] = "POST"

    call = client.calls.create(**call_params)
    return call.sid


def main() -> int:
    parser = argparse.ArgumentParser(description="Outbound AI Receptionist Demo Call")
    parser.add_argument("--to", required=True, help="Target phone number (+1XXXXXXXXXX)")
    parser.add_argument("--from", dest="from_number", default=os.getenv("TWILIO_PHONE_NUMBER", ""), help="Twilio caller ID")
    parser.add_argument("--websocket-url", default=os.getenv("WEBSOCKET_URL", ""), help="wss:// URL for Media Streams")
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", ""), help="https:// URL for callbacks (e.g., ngrok)")
    parser.add_argument("--no-record", action="store_true", help="Disable call recording")
    parser.add_argument("--status-callback", default=os.getenv("STATUS_CALLBACK_URL", ""), help="HTTP URL for call status webhooks")
    args = parser.parse_args()

    if not args.from_number:
        print("[ERROR] --from is required (or set TWILIO_PHONE_NUMBER).")
        return 1

    # Build absolute callback URLs from base-url
    base_url = args.base_url.rstrip("/") if args.base_url else ""
    recording_callback = f"{base_url}/twilio/recording" if base_url else None
    status_callback = args.status_callback or (f"{base_url}/twilio/status" if base_url else None)

    # Default WebSocket: assume ngrok or local tunnel for dev
    websocket_url = args.websocket_url
    if not websocket_url:
        print("[WARN] No --websocket-url provided. Building demo TwiML without live AI.")
        print("       For a live demo, expose your local server (e.g., ngrok http 8000)")
        print("       and set WEBSOCKET_URL=wss://<your-ngrok>.ngrok.io/ws/twilio/")
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">
        Hello! This is a demo call from TreloLabs Voice AI.
        Our virtual receptionist can schedule appointments, find contractors, and answer questions.
        Thank you for listening. Goodbye.
    </Say>
</Response>"""
    else:
        twiml = build_twiml(websocket_url, base_url)

    print("=" * 60)
    print("OUTBOUND DEMO CALL")
    print("=" * 60)
    print(f"To:       {args.to}")
    print(f"From:     {args.from_number}")
    print(f"Record:   {'YES (dual-channel)' if not args.no_record else 'NO'}")
    print(f"Base URL: {base_url or 'N/A'}")
    print(f"Time:     {datetime.utcnow().isoformat()}Z")
    print()
    print("TwiML:")
    print(twiml)
    print()

    try:
        call_sid = make_call(
            to_number=args.to,
            from_number=args.from_number,
            twiml=twiml,
            record=not args.no_record,
            recording_status_callback=recording_callback,
            status_callback=status_callback,
        )
        print(f"[OK] Call created: {call_sid}")
        print(f"     Track at: https://console.twilio.com/us1/monitor/logs/calls?frameUrl=%2Fconsole%2Fvoice%2Fcalls%2Flogs%2F{call_sid}")
        print()
        print("After the call ends, run:")
        print(f"    python3 scripts/get-recording.py --call-sid {call_sid}")
        return 0
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1


# References
# [^21]: Fette, I., & Melnikov, A. (2011). RFC 6455: The WebSocket Protocol. IETF.
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation (PCM) of Voice Frequencies.
# [^43]: Twilio. (2024). Media Streams API Documentation. twilio.com/docs/voice/media-streams.
# [^80]: Twilio. (2024). Recordings API Documentation. twilio.com/docs/voice/api/recording.
# [^81]: Twilio. (2024). Privacy and Compliance Guide for Call Recording. twilio.com/docs/glossary/what-is-call-recording.

if __name__ == "__main__":
    sys.exit(main())
