"""
Outbound Call Trigger — Jaya High School Telugu Fee Call
=========================================================
Dials a parent's number via Twilio and connects them to the AI voice
agent running locally (exposed via ngrok).

Usage:
    python scripts/make_call.py --to +919502731467 --ngrok https://xxxx.ngrok-free.app

Or if PUBLIC_DOMAIN is set in .env:
    python scripts/make_call.py --to +919502731467

The script:
  1. Loads .env
  2. Dials `--to` from TWILIO_PHONE_NUMBER
  3. Points Twilio's TwiML callback at <ngrok_url>/twilio/inbound
     with ?domain=education&language=te-IN&parent_phone=<to>
     so the agent greets in Telugu from the very first turn.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Load .env from project root
_ROOT = Path(__file__).parent.parent
_ENV  = _ROOT / ".env"
if _ENV.exists():
    for line in _ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Dial a parent via Twilio → Telugu AI agent")
    parser.add_argument("--to",       required=True,  help="Destination in E.164 format, e.g. +919502731467")
    parser.add_argument("--ngrok",    default="",     help="Public ngrok URL, e.g. https://xxxx.ngrok-free.app")
    parser.add_argument("--language", default="te-IN",help="BCP-47 language to pre-seed (default: te-IN)")
    parser.add_argument("--domain",   default="education", help="Domain id (default: education)")
    args = parser.parse_args()

    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "")
    public_domain = args.ngrok.rstrip("/") or os.getenv("PUBLIC_DOMAIN", "")

    # Validate
    errors = []
    if not account_sid: errors.append("TWILIO_ACCOUNT_SID")
    if not auth_token:  errors.append("TWILIO_AUTH_TOKEN")
    if not from_number: errors.append("TWILIO_PHONE_NUMBER")
    if not public_domain:
        errors.append(
            "ngrok URL (pass --ngrok https://xxxx.ngrok-free.app "
            "or set PUBLIC_DOMAIN in .env)"
        )
    if errors:
        print("\n[ERROR] Missing required config:")
        for e in errors:
            print(f"  • {e}")
        sys.exit(1)

    if not public_domain.startswith("http"):
        public_domain = "https://" + public_domain

    webhook_url = (
        f"{public_domain}/twilio/inbound"
        f"?domain={args.domain}"
        f"&language={args.language}"
        f"&parent_phone={args.to}"
    )
    status_url = f"{public_domain}/twilio/status"

    print(f"\nDialing   : {args.to}")
    print(f"From      : {from_number}")
    print(f"Language  : {args.language}  (pre-seeded — greeting will be in Telugu)")
    print(f"Webhook   : {webhook_url}")
    print()

    try:
        from twilio.rest import Client
    except ImportError:
        print("[ERROR] twilio package not installed. Run: pip install twilio")
        sys.exit(1)

    client = Client(account_sid, auth_token)
    call = client.calls.create(
        to=args.to,
        from_=from_number,
        url=webhook_url,
        status_callback=status_url,
        status_callback_event=["initiated", "ringing", "answered", "completed"],
    )

    print(f"[OK] Call initiated!")
    print(f"     Call SID : {call.sid}")
    print(f"     Status   : {call.status}")
    print()
    print("The agent will greet in Telugu (Namaskaram) as soon as the call is answered.")
    print("Watch server logs for real-time events.")


if __name__ == "__main__":
    main()
