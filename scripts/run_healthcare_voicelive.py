#!/usr/bin/env python3
# ruff: noqa: E402
"""
Run the Healthcare Patient Follow-Up agent with Azure VoiceLive (GPT-4.1 real-time).

Usage:
    export AZURE_VOICELIVE_API_KEY="..."
    export AZURE_VOICELIVE_ENDPOINT="https://<resource>.services.ai.azure.com/"
    python scripts/run_healthcare_voicelive.py --phone +919876543210

The script loads the seeded patient record by phone, builds the goal-engineered
instructions, registers the healthcare toolset for function calling, and starts
a real-time audio conversation.

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
from src.domains.healthcare_mvp.seed import (
    get_patient_by_phone,
    set_follow_up_log_path,
)
from src.domains.healthcare_mvp.tools import (
    EscalationTool,
    LookupPatientTool,
    RecordMedicineAdherenceTool,
    RecordSideEffectTool,
    RecordSymptomTool,
    SaveFollowUpSummaryTool,
    ScheduleFollowupTool,
)
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


def _build_tool_wrappers(patients: dict):
    """Create healthcare tool instances and expose sync wrappers for VoiceLive."""
    symptom_tool = RecordSymptomTool()
    adherence_tool = RecordMedicineAdherenceTool()
    side_effect_tool = RecordSideEffectTool()
    schedule_tool = ScheduleFollowupTool()
    escalation_tool = EscalationTool()
    save_tool = SaveFollowUpSummaryTool(
        symptom_tool=symptom_tool,
        adherence_tool=adherence_tool,
        side_effect_tool=side_effect_tool,
        schedule_tool=schedule_tool,
    )

    async def lookup_patient(phone: str):
        """Find patient details by phone number."""
        return (await LookupPatientTool(patients).execute(phone=phone)).data

    async def record_symptom(patient_id: str, symptom: str, severity: str = "mild"):
        """Record a symptom reported by the patient."""
        return (await symptom_tool.execute(patient_id=patient_id, symptom=symptom, severity=severity)).data

    async def record_medicine_adherence(
        patient_id: str, taking_medicines: str, missed_reason: str = ""
    ):
        """Record the patient's medicine adherence."""
        return (
            await adherence_tool.execute(
                patient_id=patient_id,
                taking_medicines=taking_medicines,
                missed_reason=missed_reason,
            )
        ).data

    async def record_side_effect(patient_id: str, side_effect: str, serious: bool = False):
        """Record a side effect reported by the patient."""
        return (
            await side_effect_tool.execute(
                patient_id=patient_id, side_effect=side_effect, serious=serious
            )
        ).data

    async def schedule_followup(
        patient_id: str, followup_type: str, reason: str, preferred_time: str = ""
    ):
        """Schedule a follow-up callback or appointment reminder."""
        return (
            await schedule_tool.execute(
                patient_id=patient_id,
                followup_type=followup_type,
                reason=reason,
                preferred_time=preferred_time,
            )
        ).data

    async def escalate_to_care_team(patient_id: str, reason: str):
        """Flag a call for immediate doctor or nurse attention."""
        return (await escalation_tool.execute(patient_id=patient_id, reason=reason)).data

    async def save_follow_up_summary(
        patient_id: str,
        call_id: str,
        well_being_status: str,
        escalation_needed: bool = False,
        escalation_reason: str = "",
        callback_requested: bool = False,
        notes: str = "",
    ):
        """Persist the follow-up call summary for hospital dashboard review."""
        result = await save_tool.execute(
            patient_id=patient_id,
            call_id=call_id,
            well_being_status=well_being_status,
            escalation_needed=escalation_needed,
            escalation_reason=escalation_reason,
            callback_requested=callback_requested,
            notes=notes,
        )
        return result.data

    # Attach JSON schemas so VoiceLive knows the parameters.
    lookup_patient.parameters = {
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "description": "Patient phone number including country code, e.g. +919876543210",
            },
        },
        "required": ["phone"],
    }
    record_symptom.parameters = {
        "type": "object",
        "properties": {
            "patient_id": {"type": "string"},
            "symptom": {"type": "string"},
            "severity": {"type": "string", "enum": ["mild", "moderate", "severe"]},
        },
        "required": ["patient_id", "symptom"],
    }
    record_medicine_adherence.parameters = {
        "type": "object",
        "properties": {
            "patient_id": {"type": "string"},
            "taking_medicines": {"type": "string", "enum": ["yes", "no", "partially", "unsure"]},
            "missed_reason": {"type": "string"},
        },
        "required": ["patient_id", "taking_medicines"],
    }
    record_side_effect.parameters = {
        "type": "object",
        "properties": {
            "patient_id": {"type": "string"},
            "side_effect": {"type": "string"},
            "serious": {"type": "boolean"},
        },
        "required": ["patient_id", "side_effect"],
    }
    schedule_followup.parameters = {
        "type": "object",
        "properties": {
            "patient_id": {"type": "string"},
            "followup_type": {
                "type": "string",
                "enum": ["doctor_callback", "nurse_callback", "appointment_reminder"],
            },
            "reason": {"type": "string"},
            "preferred_time": {"type": "string"},
        },
        "required": ["patient_id", "followup_type", "reason"],
    }
    escalate_to_care_team.parameters = {
        "type": "object",
        "properties": {
            "patient_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["patient_id", "reason"],
    }
    save_follow_up_summary.parameters = {
        "type": "object",
        "properties": {
            "patient_id": {"type": "string"},
            "call_id": {"type": "string"},
            "well_being_status": {
                "type": "string",
                "enum": ["improving", "same", "worse", "concerning"],
            },
            "escalation_needed": {"type": "boolean"},
            "escalation_reason": {"type": "string"},
            "callback_requested": {"type": "boolean"},
            "notes": {"type": "string"},
        },
        "required": ["patient_id", "call_id", "well_being_status"],
    }

    return {
        "lookup_patient": lookup_patient,
        "record_symptom": record_symptom,
        "record_medicine_adherence": record_medicine_adherence,
        "record_side_effect": record_side_effect,
        "schedule_followup": schedule_followup,
        "escalate_to_care_team": escalate_to_care_team,
        "save_follow_up_summary": save_follow_up_summary,
    }


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
    parser.add_argument(
        "--no-tools",
        help="Disable function calling (instructions-only mode).",
        action="store_true",
        default=False,
    )
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

    # Configure JSONL persistence for follow-up records.
    log_path = os.getenv("HEALTHCARE_FOLLOW_UP_LOG", "./healthcare_follow_ups.jsonl")
    set_follow_up_log_path(log_path)

    # Build the healthcare toolset for function calling.
    from src.domains.healthcare_mvp.seed import seed_healthcare_db

    patients = seed_healthcare_db()["patients"]
    tools = None if args.no_tools else _build_tool_wrappers(patients)

    if tools:
        print(f"🛠️  Function calling enabled with {len(tools)} tools")
    else:
        print("🛠️  Function calling disabled (instructions-only mode)")

    assistant = HealthcareVoiceLiveAssistant(
        endpoint=args.endpoint,
        credential=credential,
        model=args.model,
        voice=args.voice,
        instructions=instructions,
        tools=tools,
        proactive_greeting=True,
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
