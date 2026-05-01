"""
Retrieve Call Recording from Twilio
====================================
Polls Twilio for recordings associated with a Call SID and downloads
the audio file (WAV or MP3).

Usage:
    python scripts/get-recording.py --call-sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Or list recent recordings:
    python scripts/get-recording.py --recent 5

Research Provenance:
    - Twilio Recordings API supports dual-channel and async delivery [^80].
    - One-party consent is federally permissible; state laws vary [^81].
"""

from __future__ import annotations

import os
import sys
import argparse
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    load_dotenv(dotenv_path=str(_env))

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
RECORDINGS_DIR = PROJECT_ROOT / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)

try:
    from twilio.rest import Client
except ImportError:
    print("[ERROR] twilio Python SDK not installed.")
    sys.exit(1)


def get_recordings_for_call(call_sid: str) -> list:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    client = Client(account_sid, auth_token)

    recordings = list(client.recordings.list(call_sid=call_sid))
    return recordings


def list_recent_recordings(limit: int = 10) -> list:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    client = Client(account_sid, auth_token)

    return list(client.recordings.list(limit=limit))


def download_recording(recording_url: str, filename: str) -> Path:
    """Download recording from Twilio (append .wav for raw audio)."""
    # Twilio requires basic auth even for public recording URLs
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()

    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, recording_url, account_sid, auth_token)
    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    opener = urllib.request.build_opener(handler)

    dest = RECORDINGS_DIR / filename
    with opener.open(recording_url) as response:
        with open(dest, "wb") as f:
            f.write(response.read())
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve Twilio Call Recordings")
    parser.add_argument("--call-sid", help="Call SID to fetch recordings for")
    parser.add_argument("--recent", type=int, help="List N most recent recordings")
    args = parser.parse_args()

    if args.recent:
        print(f"Recent {args.recent} recordings:")
        recordings = list_recent_recordings(args.recent)
        for r in recordings:
            print(f"  {r.sid} | {r.duration}s | {r.date_created} | {r.uri}")
        return 0

    if not args.call_sid:
        print("[ERROR] --call-sid or --recent required.")
        return 1

    print(f"Fetching recordings for call {args.call_sid} ...")
    recordings = get_recordings_for_call(args.call_sid)

    if not recordings:
        print("[WARN] No recordings found yet. Wait 30-60 seconds after call ends and retry.")
        return 1

    for r in recordings:
        # Build download URL (Twilio recordings are .wav by default)
        url = f"https://api.twilio.com{r.uri.replace('.json', '.wav')}"
        filename = f"{r.sid}_{args.call_sid}.wav"
        print(f"  Downloading {r.sid} ({r.duration}s) ...")
        dest = download_recording(url, filename)
        print(f"  Saved: {dest}")

    print(f"\nAll recordings saved to: {RECORDINGS_DIR}")
    return 0


# References
# [^80]: Twilio. (2024). Recordings API Documentation.
# [^81]: Twilio. (2024). Privacy and Compliance Guide for Call Recording.

if __name__ == "__main__":
    sys.exit(main())
