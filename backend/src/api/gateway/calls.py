"""
Gateway Call Routes
Call history, active calls, transcripts, and call control.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from src.api.gateway.db import GatewayDB, CallLog, TranscriptRow
from src.api.gateway.models import (
    CallOut,
    CallListResponse,
    ActiveCallOut,
    TranscriptLineOut,
    TriggerCallRequest,
)
from src.infrastructure.call_state import CallStateManager

router = APIRouter(prefix="/gateway/v1/calls", tags=["gateway-calls"])
_db = GatewayDB()
_state = CallStateManager()
DEFAULT_TENANT = "lincoln-high"


def _call_to_out(c: CallLog) -> CallOut:
    return CallOut(
        id=c.id,
        call_sid=c.call_sid,
        tenant_id=c.tenant_id,
        student_id=c.student_id,
        student_name=None,  # Can be joined later
        domain=c.domain,
        direction=c.direction,
        phone_to=c.phone_to,
        phone_from=c.phone_from,
        status=c.status,
        call_type=c.call_type,
        duration_seconds=c.duration_seconds,
        transcript_summary=c.transcript_summary,
        created_at=c.created_at,
        ended_at=c.ended_at,
    )


@router.get("", response_model=CallListResponse)
async def list_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    tenant_id: str = DEFAULT_TENANT,
):
    items, total = await _db.list_call_logs(tenant_id, page, page_size, status)
    return CallListResponse(
        items=[_call_to_out(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/active", response_model=List[ActiveCallOut])
async def list_active_calls():
    active = _state.get_active_calls()
    return [
        ActiveCallOut(
            call_sid=c.call_sid,
            student_name=c.student_name,
            parent_name=c.parent_name,
            call_type=c.call_type,
            duration_seconds=c.duration_seconds,
            status=c.status,
            transcript_count=len(c.transcripts),
        )
        for c in active
    ]


@router.get("/{call_sid}/transcript", response_model=List[TranscriptLineOut])
async def get_transcript(call_sid: str):
    rows = await _db.get_transcripts_for_call(call_sid)
    return [
        TranscriptLineOut(speaker=r.speaker, text=r.text, timestamp_ms=r.timestamp_ms)
        for r in rows
    ]


@router.post("/{call_sid}/terminate")
async def terminate_call(call_sid: str):
    call = _state.get_call(call_sid)
    if call is None:
        raise HTTPException(status_code=404, detail="Active call not found")

    await _state.finalize_call(call_sid, status="terminated")
    # Persist final state
    existing = await _db.get_call_log_by_sid(call_sid)
    if existing:
        await _db.update_call_log(call_sid, {
            "status": "terminated",
            "duration_seconds": call.duration_seconds,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        })
    return {"status": "terminated", "call_sid": call_sid}


@router.post("/trigger")
async def trigger_call(body: TriggerCallRequest, tenant_id: str = DEFAULT_TENANT):
    """
    Trigger an outbound call. In production this delegates to the voice
    pipeline outbound caller. For now, returns the call parameters.
    """
    # TODO: integrate with OutboundCaller from receptionist layer
    return {
        "status": "queued",
        "parent_phone": body.parent_phone,
        "language": body.language,
        "domain": body.domain,
        "call_type": body.call_type,
        "message": "Call queued. Voice pipeline will initiate.",
    }
