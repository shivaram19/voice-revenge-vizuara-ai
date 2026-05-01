"""
CRM API scaffold endpoints for frontend integration.
Provides stable contracts for the Next.js Voice CRM workspace.
"""

from datetime import datetime
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/crm", tags=["crm"])


@router.get("/summary")
async def crm_summary() -> dict:
    """Top-level counters used by CRM dashboard cards."""
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "kpis": {
            "needs_attention": 7,
            "live_calls": 11,
            "at_risk_sla": 3,
            "booked_today": 29,
        },
    }


@router.get("/interactions")
async def crm_interactions() -> dict:
    """Active interactions list for operator queue UI."""
    return {
        "items": [
            {
                "id": "VC-201",
                "caller": "Aarav Patel",
                "reason": "Water leak emergency",
                "stage": "Live",
                "queue": "Emergency",
                "elapsed": "02:41",
                "priority": "P1",
            },
            {
                "id": "VC-202",
                "caller": "Neha Builders",
                "reason": "Schedule site visit",
                "stage": "Ringing",
                "queue": "Scheduling",
                "elapsed": "00:22",
                "priority": "P2",
            },
            {
                "id": "VC-203",
                "caller": "Karan Singh",
                "reason": "Invoice clarification",
                "stage": "WrapUp",
                "queue": "Billing",
                "elapsed": "01:09",
                "priority": "P3",
            },
        ]
    }


@router.get("/transcript/{interaction_id}")
async def crm_transcript(interaction_id: str) -> dict:
    """Transcript payload for selected interaction."""
    return {
        "interaction_id": interaction_id,
        "lines": [
            {"speaker": "Caller", "text": "There is active leakage from the second floor ceiling."},
            {"speaker": "Agent", "text": "I can help. Is electricity turned off in that section?"},
            {"speaker": "Caller", "text": "Yes, done. We need technician ETA."},
            {"speaker": "Agent", "text": "Dispatching emergency team now. Expected arrival in 35 minutes."},
        ],
    }
