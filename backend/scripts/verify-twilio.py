"""
Twilio Credential Verification Script
======================================
Validates account status, lists provisioned phone numbers, and checks
usable balance before outbound demo calls.

Usage:
    export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    export TWILIO_AUTH_TOKEN="your_auth_token"
    python scripts/verify-twilio.py

Ref: Twilio REST API design follows state-transfer principles consistent
with Fielding (2000) [^79].

Research Provenance:
    - Twilio Media Streams use WebSocket with 8 kHz μ-law [^43].
    - μ-law companding: ITU-T G.711 (1972) reduces 14-bit dynamic range
      to 8 bits with ~33 dB SNR [^38].
    - WebSocket protocol (RFC 6455) provides full-duplex, ordered,
      message-oriented transport over TCP [^21].
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    load_dotenv(dotenv_path=str(_env))

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from twilio.rest import Client
except ImportError:
    print("[ERROR] twilio Python SDK not installed.")
    print("        pip install twilio")
    sys.exit(1)


def verify() -> int:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()

    if not account_sid or not auth_token:
        print("[ERROR] Missing Twilio credentials.")
        print("        export TWILIO_ACCOUNT_SID='AC...'")
        print("        export TWILIO_AUTH_TOKEN='...'")
        return 1

    print("=" * 60)
    print("TWILIO CREDENTIAL VERIFICATION")
    print("=" * 60)

    client = Client(account_sid, auth_token)

    # 1. Account info
    try:
        account = client.api.accounts(account_sid).fetch()
        print(f"\n[OK] Account SID:   {account.sid}")
        print(f"[OK] Friendly Name: {account.friendly_name}")
        print(f"[OK] Status:        {account.status}")
        print(f"[OK] Type:          {account.type}")
    except Exception as exc:
        print(f"\n[FAIL] Cannot fetch account: {exc}")
        return 1

    # 2. Balance check (trial accounts show 0; paid accounts show USD balance)
    try:
        balance = client.api.account.balance.fetch()
        print(f"[OK] Balance:       {balance.balance} {balance.currency}")
        if float(balance.balance) <= 0.0 and account.type == "Trial":
            print("[WARN] Trial account detected. Upgrade to make calls to non-verified numbers.")
    except Exception:
        print("[INFO] Balance endpoint unavailable for this account type.")

    # 3. Phone numbers
    try:
        numbers = list(client.incoming_phone_numbers.list(limit=20))
        print(f"\n[OK] Provisioned phone numbers: {len(numbers)}")
        for num in numbers:
            caps = []
            if num.capabilities.get("voice"):
                caps.append("voice")
            if num.capabilities.get("sms"):
                caps.append("sms")
            print(f"       {num.phone_number}  ({', '.join(caps)})  — {num.friendly_name or 'Unnamed'}")
        if not numbers:
            print("[WARN] No phone numbers found. Buy one at https://console.twilio.com")
    except Exception as exc:
        print(f"[FAIL] Cannot list numbers: {exc}")
        return 1

    # 4. Outbound caller ID validation
    verified = []
    try:
        verified = list(client.outgoing_caller_ids.list(limit=20))
        print(f"\n[OK] Verified caller IDs: {len(verified)}")
        for cid in verified:
            print(f"       {cid.phone_number}")
    except Exception:
        pass

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

    if not numbers:
        print("\nNEXT STEP: Purchase a Twilio phone number before making calls.")
        return 1

    if account.type == "Trial" and not verified:
        print("\nNEXT STEP: Trial accounts can only call verified numbers.")
        print("           Verify your phone at https://console.twilio.com")
        return 1

    print("\nYou are ready to make outbound demo calls.")
    print("Run: python scripts/demo-outbound-call.py")
    return 0


# References
# [^21]: Fette, I., & Melnikov, A. (2011). RFC 6455: The WebSocket Protocol. IETF.
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation (PCM) of Voice Frequencies.
# [^43]: Twilio. (2024). Media Streams API Documentation. twilio.com/docs/voice/media-streams.
# [^79]: Fielding, R. T. (2000). Architectural Styles and the Design of Network-based Software Architectures. PhD thesis, UC Irvine.

if __name__ == "__main__":
    sys.exit(verify())
