"""
Gateway Database Layer — Prisma ORM
PostgreSQL-backed persistence for education-domain entities.
Maintains the same public interface as the old SQLite version
so route files require minimal changes (just add `await`).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.infrastructure.database import prisma


# ---------------------------------------------------------------------------
# Dataclasses (kept for backward compatibility with route converters)
# ---------------------------------------------------------------------------

@dataclass
class Student:
    id: Optional[int]
    tenant_id: str
    name: str
    grade: str
    parent_name: str
    parent_phone: str
    attendance_status: str
    recent_call_summary: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CallLog:
    id: Optional[int]
    call_sid: str
    tenant_id: str
    student_id: Optional[int]
    domain: Optional[str]
    direction: Optional[str]
    phone_to: Optional[str]
    phone_from: Optional[str]
    status: Optional[str]
    call_type: Optional[str]
    duration_seconds: int
    transcript_summary: Optional[str]
    created_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


@dataclass
class TranscriptRow:
    id: Optional[int]
    call_sid: str
    speaker: str
    text: str
    timestamp_ms: int
    created_at: Optional[datetime] = None


@dataclass
class Tenant:
    id: Optional[int]
    tenant_id: str
    name: str
    district: Optional[str]
    admin_email: Optional[str]
    student_count_range: Optional[str]
    created_at: Optional[datetime] = None


@dataclass
class User:
    id: Optional[int]
    email: str
    password: Optional[str]
    full_name: Optional[str]
    role: Optional[str]
    tenant_id: Optional[str]
    avatar_seed: Optional[str]
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# GatewayDB — async Prisma wrapper
# ---------------------------------------------------------------------------

class GatewayDB:
    """Prisma-backed gateway database. All methods are async."""

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    async def seed_demo_data(self, tenant_id: str = "lincoln-high") -> None:
        """Seed with demo data matching frontend mock data."""
        # Seed tenant
        await prisma.tenant.upsert(
            where={"tenant_id": tenant_id},
            data={
                "create": {
                    "tenant_id": tenant_id,
                    "name": "Lincoln High School",
                    "district": "District 12",
                    "admin_email": "admin@school.edu",
                    "student_count_range": "1000-1500",
                },
                "update": {},
            },
        )

        # Seed users matching mock-auth.ts
        await prisma.user.upsert(
            where={"email": "admin@school.edu"},
            data={
                "create": {
                    "email": "admin@school.edu",
                    "password": "password123",
                    "full_name": "Dr. Sarah Mitchell",
                    "role": "Principal",
                    "tenant_id": tenant_id,
                    "avatar_seed": "Principal",
                },
                "update": {},
            },
        )
        await prisma.user.upsert(
            where={"email": "teacher@school.edu"},
            data={
                "create": {
                    "email": "teacher@school.edu",
                    "password": "password123",
                    "full_name": "Mr. James Okafor",
                    "role": "Teacher",
                    "tenant_id": tenant_id,
                    "avatar_seed": "Teacher",
                },
                "update": {},
            },
        )

        # Seed students matching frontend mock
        students = [
            (tenant_id, "Emma Thompson", "10th Grade", "Sarah Thompson", "+1 (555) 123-4567", "Present", "Absence (Resolved)"),
            (tenant_id, "James Wilson", "11th Grade", "Michael Wilson", "+1 (555) 987-6543", "Absent", "Fee Reminder (Failed)"),
            (tenant_id, "Sophia Martinez", "9th Grade", "Elena Martinez", "+1 (555) 456-7890", "Present", "Announcement (Delivered)"),
            (tenant_id, "Liam Garcia", "12th Grade", "Maria Garcia", "+1 (555) 234-5678", "Absent", "Absence Follow-up (Active)"),
            (tenant_id, "Olivia Brown", "10th Grade", "David Brown", "+1 (555) 345-6789", "Present", "None"),
        ]
        existing = await prisma.student.count(where={"tenant_id": tenant_id})
        if existing == 0:
            for s in students:
                await prisma.student.create(
                    data={
                        "tenant_id": s[0],
                        "name": s[1],
                        "grade": s[2],
                        "parent_name": s[3],
                        "parent_phone": s[4],
                        "attendance_status": s[5],
                        "recent_call_summary": s[6],
                    }
                )

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def create_user(self, user: User) -> int:
        created = await prisma.user.create(
            data={
                "email": user.email,
                "password": user.password,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_id": user.tenant_id,
                "avatar_seed": user.avatar_seed,
            }
        )
        return created.id

    async def get_user_by_email(self, email: str) -> Optional[User]:
        row = await prisma.user.find_unique(where={"email": email})
        return self._row_to_user(row) if row else None

    def _row_to_user(self, row) -> User:
        return User(
            id=row.id,
            email=row.email,
            password=row.password,
            full_name=row.full_name,
            role=row.role,
            tenant_id=row.tenant_id,
            avatar_seed=row.avatar_seed,
            created_at=row.created_at,
        )

    # ------------------------------------------------------------------
    # Tenants
    # ------------------------------------------------------------------

    async def create_tenant(self, tenant: Tenant) -> int:
        created = await prisma.tenant.create(
            data={
                "tenant_id": tenant.tenant_id,
                "name": tenant.name,
                "district": tenant.district,
                "admin_email": tenant.admin_email,
                "student_count_range": tenant.student_count_range,
            }
        )
        return created.id

    async def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        row = await prisma.tenant.find_unique(where={"tenant_id": tenant_id})
        return self._row_to_tenant(row) if row else None

    def _row_to_tenant(self, row) -> Tenant:
        return Tenant(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            district=row.district,
            admin_email=row.admin_email,
            student_count_range=row.student_count_range,
            created_at=row.created_at,
        )

    # ------------------------------------------------------------------
    # Students
    # ------------------------------------------------------------------

    async def create_student(self, student: Student) -> int:
        created = await prisma.student.create(
            data={
                "tenant_id": student.tenant_id,
                "name": student.name,
                "grade": student.grade,
                "parent_name": student.parent_name,
                "parent_phone": student.parent_phone,
                "attendance_status": student.attendance_status,
                "recent_call_summary": student.recent_call_summary,
            }
        )
        return created.id

    async def get_student(self, student_id: int) -> Optional[Student]:
        row = await prisma.student.find_unique(where={"id": student_id})
        return self._row_to_student(row) if row else None

    async def update_student(self, student_id: int, fields: Dict[str, Any]) -> bool:
        allowed = {"name", "grade", "parent_name", "parent_phone", "attendance_status", "recent_call_summary"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return False
        try:
            await prisma.student.update(where={"id": student_id}, data=updates)
            return True
        except Exception:
            return False

    async def delete_student(self, student_id: int) -> bool:
        try:
            await prisma.student.delete(where={"id": student_id})
            return True
        except Exception:
            return False

    async def list_students(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        grade: Optional[str] = None,
    ) -> tuple[List[Student], int]:
        where: Dict[str, Any] = {"tenant_id": tenant_id}
        if grade:
            where["grade"] = grade
        if search:
            where["OR"] = [
                {"name": {"contains": search, "mode": "insensitive"}},
                {"parent_name": {"contains": search, "mode": "insensitive"}},
                {"parent_phone": {"contains": search, "mode": "insensitive"}},
            ]

        total = await prisma.student.count(where=where)
        rows = await prisma.student.find_many(
            where=where,
            skip=(page - 1) * page_size,
            take=page_size,
            order={"name": "asc"},
        )
        return [self._row_to_student(r) for r in rows], total

    def _row_to_student(self, row) -> Student:
        return Student(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            grade=row.grade,
            parent_name=row.parent_name,
            parent_phone=row.parent_phone,
            attendance_status=row.attendance_status,
            recent_call_summary=row.recent_call_summary,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    # ------------------------------------------------------------------
    # Call Logs
    # ------------------------------------------------------------------

    async def create_call_log(self, call: CallLog) -> int:
        created = await prisma.calllog.create(
            data={
                "call_sid": call.call_sid,
                "tenant_id": call.tenant_id,
                "student_id": call.student_id,
                "domain": call.domain,
                "direction": call.direction,
                "phone_to": call.phone_to,
                "phone_from": call.phone_from,
                "status": call.status,
                "call_type": call.call_type,
                "duration_seconds": call.duration_seconds,
                "transcript_summary": call.transcript_summary,
            }
        )
        return created.id

    async def get_call_log(self, call_log_id: int) -> Optional[CallLog]:
        row = await prisma.calllog.find_unique(where={"id": call_log_id})
        return self._row_to_call_log(row) if row else None

    async def get_call_log_by_sid(self, call_sid: str) -> Optional[CallLog]:
        row = await prisma.calllog.find_unique(where={"call_sid": call_sid})
        return self._row_to_call_log(row) if row else None

    async def update_call_log(self, call_sid: str, fields: Dict[str, Any]) -> bool:
        allowed = {"status", "duration_seconds", "transcript_summary", "ended_at", "student_id"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return False
        try:
            await prisma.calllog.update(where={"call_sid": call_sid}, data=updates)
            return True
        except Exception:
            return False

    async def list_call_logs(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> tuple[List[CallLog], int]:
        where: Dict[str, Any] = {"tenant_id": tenant_id}
        if status:
            where["status"] = status

        total = await prisma.calllog.count(where=where)
        rows = await prisma.calllog.find_many(
            where=where,
            skip=(page - 1) * page_size,
            take=page_size,
            order={"created_at": "desc"},
        )
        return [self._row_to_call_log(r) for r in rows], total

    def _row_to_call_log(self, row) -> CallLog:
        return CallLog(
            id=row.id,
            call_sid=row.call_sid,
            tenant_id=row.tenant_id,
            student_id=row.student_id,
            domain=row.domain,
            direction=row.direction,
            phone_to=row.phone_to,
            phone_from=row.phone_from,
            status=row.status,
            call_type=row.call_type,
            duration_seconds=row.duration_seconds,
            transcript_summary=row.transcript_summary,
            created_at=row.created_at,
            ended_at=row.ended_at,
        )

    # ------------------------------------------------------------------
    # Transcripts
    # ------------------------------------------------------------------

    async def create_transcript(self, t: TranscriptRow) -> int:
        created = await prisma.transcript.create(
            data={
                "call_sid": t.call_sid,
                "speaker": t.speaker,
                "text": t.text,
                "timestamp_ms": t.timestamp_ms,
            }
        )
        return created.id

    async def get_transcripts_for_call(self, call_sid: str) -> List[TranscriptRow]:
        rows = await prisma.transcript.find_many(
            where={"call_sid": call_sid},
            order={"timestamp_ms": "asc"},
        )
        return [self._row_to_transcript(r) for r in rows]

    def _row_to_transcript(self, row) -> TranscriptRow:
        return TranscriptRow(
            id=row.id,
            call_sid=row.call_sid,
            speaker=row.speaker,
            text=row.text,
            timestamp_ms=row.timestamp_ms,
            created_at=row.created_at,
        )
