"""
AI Receptionist Data Models — Prisma ORM
PostgreSQL-backed models for appointments, contractors, and call tasks.
Maintains the same public interface; methods are now async.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import List, Optional
from enum import Enum

from src.infrastructure.database import prisma


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentType(str, Enum):
    IN_PERSON = "in_person"
    PHONE = "phone"
    VIDEO = "video"


class CallTaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    DIALING = "dialing"
    CONNECTED = "connected"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Contractor:
    id: Optional[int]
    name: str
    phone: str
    email: str
    specialty: str
    timezone: str = "UTC"
    daily_limit: int = 8
    is_active: bool = True
    notes: str = ""


@dataclass
class Appointment:
    id: Optional[int]
    contractor_id: int
    caller_name: str
    caller_phone: str
    start_time: datetime
    duration_minutes: int
    status: AppointmentStatus
    appointment_type: AppointmentType
    notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class TimeSlot:
    contractor_id: int
    date: date
    start_time: datetime
    end_time: datetime
    is_available: bool = True


@dataclass
class CallTask:
    id: Optional[int]
    contractor_id: int
    purpose: str
    scheduled_time: Optional[datetime]
    status: CallTaskStatus
    twilio_call_sid: Optional[str] = None
    result_notes: str = ""
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Database:
    """Prisma-backed receptionist database. All methods are async."""

    # -----------------------------------------------------------------------
    # Contractors
    # -----------------------------------------------------------------------

    async def add_contractor(self, c: Contractor) -> int:
        created = await prisma.contractor.create(
            data={
                "name": c.name,
                "phone": c.phone,
                "email": c.email,
                "specialty": c.specialty,
                "timezone": c.timezone,
                "daily_limit": c.daily_limit,
                "is_active": c.is_active,
                "notes": c.notes,
            }
        )
        return created.id

    async def get_contractor(self, contractor_id: int) -> Optional[Contractor]:
        row = await prisma.contractor.find_unique(where={"id": contractor_id})
        return self._row_to_contractor(row) if row else None

    async def list_contractors(self, active_only: bool = True) -> List[Contractor]:
        where = {"is_active": True} if active_only else {}
        rows = await prisma.contractor.find_many(where=where)
        return [self._row_to_contractor(r) for r in rows]

    async def find_contractors_by_specialty(self, specialty: str) -> List[Contractor]:
        rows = await prisma.contractor.find_many(
            where={
                "specialty": {"contains": specialty, "mode": "insensitive"},
                "is_active": True,
            }
        )
        return [self._row_to_contractor(r) for r in rows]

    def _row_to_contractor(self, row) -> Contractor:
        return Contractor(
            id=row.id,
            name=row.name,
            phone=row.phone,
            email=row.email,
            specialty=row.specialty,
            timezone=row.timezone,
            daily_limit=row.daily_limit,
            is_active=row.is_active,
            notes=row.notes,
        )

    # -----------------------------------------------------------------------
    # Appointments
    # -----------------------------------------------------------------------

    async def add_appointment(self, a: Appointment) -> int:
        created = await prisma.appointment.create(
            data={
                "contractor_id": a.contractor_id,
                "caller_name": a.caller_name,
                "caller_phone": a.caller_phone,
                "start_time": a.start_time,
                "duration_minutes": a.duration_minutes,
                "status": a.status.value,
                "appointment_type": a.appointment_type.value,
                "notes": a.notes,
            }
        )
        return created.id

    async def get_appointment(self, appointment_id: int) -> Optional[Appointment]:
        row = await prisma.appointment.find_unique(where={"id": appointment_id})
        return self._row_to_appointment(row) if row else None

    async def list_appointments_for_contractor(
        self,
        contractor_id: int,
        start: datetime,
        end: datetime,
        status_filter: Optional[List[AppointmentStatus]] = None,
    ) -> List[Appointment]:
        where: dict = {
            "contractor_id": contractor_id,
            "start_time": {"gte": start, "lte": end},
        }
        if status_filter:
            where["status"] = {"in": [s.value for s in status_filter]}

        rows = await prisma.appointment.find_many(where=where)
        return [self._row_to_appointment(r) for r in rows]

    async def cancel_appointment(self, appointment_id: int) -> bool:
        try:
            await prisma.appointment.update(
                where={"id": appointment_id},
                data={"status": AppointmentStatus.CANCELLED.value},
            )
            return True
        except Exception:
            return False

    async def update_appointment_status(self, appointment_id: int, status: AppointmentStatus) -> bool:
        try:
            await prisma.appointment.update(
                where={"id": appointment_id},
                data={"status": status.value},
            )
            return True
        except Exception:
            return False

    def _row_to_appointment(self, row) -> Appointment:
        return Appointment(
            id=row.id,
            contractor_id=row.contractor_id,
            caller_name=row.caller_name,
            caller_phone=row.caller_phone,
            start_time=row.start_time,
            duration_minutes=row.duration_minutes,
            status=AppointmentStatus(row.status),
            appointment_type=AppointmentType(row.appointment_type),
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    # -----------------------------------------------------------------------
    # Call Tasks
    # -----------------------------------------------------------------------

    async def add_call_task(self, t: CallTask) -> int:
        created = await prisma.calltask.create(
            data={
                "contractor_id": t.contractor_id,
                "purpose": t.purpose,
                "scheduled_time": t.scheduled_time,
                "status": t.status.value,
                "twilio_call_sid": t.twilio_call_sid,
                "result_notes": t.result_notes,
            }
        )
        return created.id

    async def get_pending_call_tasks(self, before: Optional[datetime] = None) -> List[CallTask]:
        where: dict = {
            "status": {"in": [CallTaskStatus.PENDING.value, CallTaskStatus.QUEUED.value]},
        }
        if before:
            where["OR"] = [
                {"scheduled_time": None},
                {"scheduled_time": {"lte": before}},
            ]

        rows = await prisma.calltask.find_many(where=where)
        return [self._row_to_call_task(r) for r in rows]

    async def update_call_task_status(
        self,
        task_id: int,
        status: CallTaskStatus,
        notes: str = "",
        call_sid: Optional[str] = None,
    ) -> bool:
        data: dict = {"status": status.value, "result_notes": notes}
        if call_sid:
            data["twilio_call_sid"] = call_sid
        if status in (CallTaskStatus.COMPLETED, CallTaskStatus.FAILED, CallTaskStatus.CANCELLED):
            data["completed_at"] = datetime.utcnow()
        try:
            await prisma.calltask.update(where={"id": task_id}, data=data)
            return True
        except Exception:
            return False

    def _row_to_call_task(self, row) -> CallTask:
        return CallTask(
            id=row.id,
            contractor_id=row.contractor_id,
            purpose=row.purpose,
            scheduled_time=row.scheduled_time,
            status=CallTaskStatus(row.status),
            twilio_call_sid=row.twilio_call_sid,
            result_notes=row.result_notes,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )
