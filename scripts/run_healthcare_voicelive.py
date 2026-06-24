#!/usr/bin/env python3
# ruff: noqa: E402
"""
Run the Healthcare Patient Follow-Up agent with Azure VoiceLive (GPT-4.1 real-time).

Usage:
    export AZURE_VOICELIVE_API_KEY="..."
    export AZURE_VOICELIVE_ENDPOINT="https://<resource>.services.ai.azure.com/"
    python scripts/run_healthcare_voicelive.py --phone +919876543210

The script loads the seeded patient record by phone, builds the goal-engineered
instructions, and starts a real-time audio conversation.

Ref: docs/engineering/goal-vector-healthcare-mvp.md
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on path before importing project modules.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import asyncio
import logging
import signal
from datetime import datetime

from azure.core.credentials import AzureKeyCredential
from azure.identity.aio import AzureCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

from src.domains.healthcare_mvp.prompts import build_healthcare_instructions
from src.domains.healthcare_mvp.seed import get_patient_by_phone
from src.infrastructure.azure_voicelive_assistant import (
    HealthcareVoiceLiveAssistant,
    check_audio_devices,
)


def _setup_logging(verbose: bool) -> None:
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logging.basicConfig(
        filename=str(log_dir / f"{timestamp}_healthcare_voicelive.log"),
        filemode="w",
        format="%(asctime)s:%(name)s:%(levelname)s:%(message)s",
        level=logging.DEBUG if verbose else logging.INFO,
    )


def _build_instructions(phone: str) -> str:
    patient = get_patient_by_phone(phone)
    if patient is None:
        print(f"⚠️  No seeded patient found for {phone}. Using generic instructions.")
        patient_context = {"name": "sir/madam"}
    else:
        print(f"👤 Loaded patient: {patient.name} ({patient.language_preference})")
        patient_context = {
            "patient_id": patient.patient_id,
            "name": patient.name,
            "age": patient.age,
            "language_preference": patient.language_preference,
            "diagnosis": patient.diagnosis,
            "medications": [
                {
                    "name": m.name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                    "instructions": m.instructions,
                }
                for m in patient.medications
            ],
        }

    today = datetime.now().strftime("%A, %B %d, %Y")
    instructions = build_healthcare_instructions(
        company_name="Arogya Hospital",
        hours_text="Outpatient services Monday through Saturday, 8 AM to 8 PM. Emergency 24/7.",
        today_date=today,
        patient_context=patient_context,
    )
    return instructions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Healthcare patient follow-up agent using Azure VoiceLive (GPT-4.1 real-time).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--phone",
        help="Patient phone number (must match a seeded record).",
        default=os.environ.get("HEALTHCARE_PATIENT_PHONE", "+919876543210"),
    )
    parser.add_argument(
        "--api-key",
        help="Azure VoiceLive API key. Falls back to AZURE_VOICELIVE_API_KEY env var.",
        default=os.environ.get("AZURE_VOICELIVE_API_KEY"),
    )
    parser.add_argument(
        "--endpoint",
        help="Azure VoiceLive endpoint.",
        default=os.environ.get(
            "AZURE_VOICELIVE_ENDPOINT", "https://your-resource-name.services.ai.azure.com/"
        ),
    )
    parser.add_argument(
        "--model",
        help="VoiceLive model deployment name.",
        default=os.environ.get("AZURE_VOICELIVE_MODEL", "gpt-realtime"),
    )
    parser.add_argument(
        "--voice",
        help="Voice for assistant. Azure voice names or OpenAI voices (alloy, echo, etc.).",
        default=os.environ.get("AZURE_VOICELIVE_VOICE", "en-US-Ava:DragonHDLatestNeural"),
    )
    parser.add_argument(
        "--use-token-credential",
        help="Use Azure CLI / DefaultAzureCredential instead of an API key.",
        action="store_true",
        default=False,
    )
    parser.add_argument("--verbose", help="Enable verbose logging.", action="store_true")
    return parser.parse_args()


def main() -> int:
    load_dotenv(project_root / ".env", override=True)
    args = parse_args()
    _setup_logging(args.verbose)

    if not check_audio_devices():
        return 1

    if not args.api_key and not args.use_token_credential:
        print("❌ Error: Provide --api-key or set AZURE_VOICELIVE_API_KEY, or use --use-token-credential.")
        return 1

    if args.use_token_credential:
        credential: AzureCliCredential | DefaultAzureCredential | AzureKeyCredential = (
            AzureCliCredential()
        )
        print("🔐 Using Azure token credential")
    else:
        credential = AzureKeyCredential(args.api_key)
        print("🔐 Using API key credential")

    instructions = _build_instructions(args.phone)

    assistant = HealthcareVoiceLiveAssistant(
        endpoint=args.endpoint,
        credential=credential,
        model=args.model,
        voice=args.voice,
        instructions=instructions,
    )

    def signal_handler(_sig, _frame):
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(assistant.start())
    except KeyboardInterrupt:
        print("\n👋 Healthcare assistant shut down. Goodbye!")
    except Exception as exc:
        print(f"❌ Fatal error: {exc}")
        logging.getLogger(__name__).exception("Fatal error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
