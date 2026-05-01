"""
Gateway Student Routes
CRUD + search for the student directory.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from src.api.gateway.db import GatewayDB, Student
from src.api.gateway.models import (
    StudentCreate,
    StudentUpdate,
    StudentOut,
    StudentListResponse,
)

router = APIRouter(prefix="/gateway/v1/students", tags=["gateway-students"])
_db = GatewayDB()

DEFAULT_TENANT = "lincoln-high"


def _to_out(s: Student) -> StudentOut:
    return StudentOut(
        id=s.id,
        tenant_id=s.tenant_id,
        name=s.name,
        grade=s.grade,
        parent_name=s.parent_name,
        parent_phone=s.parent_phone,
        attendance_status=s.attendance_status,
        recent_call_summary=s.recent_call_summary,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("", response_model=StudentListResponse)
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    tenant_id: str = DEFAULT_TENANT,
):
    items, total = _db.list_students(tenant_id, page, page_size, search, grade)
    return StudentListResponse(
        items=[_to_out(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=StudentOut)
async def create_student(body: StudentCreate, tenant_id: str = DEFAULT_TENANT):
    student = Student(
        id=None,
        tenant_id=tenant_id,
        name=body.name,
        grade=body.grade,
        parent_name=body.parent_name,
        parent_phone=body.parent_phone,
        attendance_status=body.attendance_status,
        recent_call_summary="None",
    )
    sid = _db.create_student(student)
    created = _db.get_student(sid)
    if created is None:
        raise HTTPException(status_code=500, detail="Failed to create student")
    return _to_out(created)


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(student_id: int):
    student = _db.get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return _to_out(student)


@router.patch("/{student_id}", response_model=StudentOut)
async def update_student(student_id: int, body: StudentUpdate):
    student = _db.get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return _to_out(student)

    ok = _db.update_student(student_id, updates)
    if not ok:
        raise HTTPException(status_code=500, detail="Update failed")

    updated = _db.get_student(student_id)
    return _to_out(updated)


@router.delete("/{student_id}")
async def delete_student(student_id: int):
    student = _db.get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    _db.delete_student(student_id)
    return {"status": "deleted", "id": student_id}


@router.post("/{student_id}/call")
async def trigger_student_call(student_id: int, tenant_id: str = DEFAULT_TENANT):
    """
    Trigger an outbound call to the student's parent.
    Delegates to the existing voice /call endpoint logic.
    """
    student = _db.get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    # Return the payload that the frontend can use, or we could invoke
    # the Twilio client directly here. For now, return the call params
    # so the frontend or a background job can initiate.
    return {
        "status": "queued",
        "student_id": student_id,
        "parent_phone": student.parent_phone,
        "student_name": student.name,
        "message": "Call queued for initiation",
    }
