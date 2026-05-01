"""
Gateway Database Layer
SQLite-backed persistence for education-domain entities:
students, call_logs, transcripts, tenants, and users.

Design:
    - Separate from receptionist.db (construction domain) to avoid coupling
    - Simple CRUD with raw SQL for clarity and zero dependency overhead
    - Ready for SQLAlchemy migration if PostgreSQL is adopted later

Refs:
    - SQLite best practices (sqlite.org)
    - 12-Factor App: config in environment for DB path
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager


# ---------------------------------------------------------------------------
# Dataclasses
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
    full_name: Optional[str]
    role: Optional[str]
    tenant_id: Optional[str]
    avatar_seed: Optional[str]
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    grade TEXT NOT NULL,
    parent_name TEXT NOT NULL,
    parent_phone TEXT NOT NULL,
    attendance_status TEXT DEFAULT 'Present',
    recent_call_summary TEXT DEFAULT 'None',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_students_tenant ON students(tenant_id);
CREATE INDEX IF NOT EXISTS idx_students_grade ON students(grade);
CREATE INDEX IF NOT EXISTS idx_students_name ON students(name);

CREATE TABLE IF NOT EXISTS call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT UNIQUE NOT NULL,
    tenant_id TEXT NOT NULL,
    student_id INTEGER,
    domain TEXT,
    direction TEXT,
    phone_to TEXT,
    phone_from TEXT,
    status TEXT,
    call_type TEXT,
    duration_seconds INTEGER DEFAULT 0,
    transcript_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_call_logs_tenant ON call_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_status ON call_logs(status);
CREATE INDEX IF NOT EXISTS idx_call_logs_created ON call_logs(created_at);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT NOT NULL,
    speaker TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transcripts_call_sid ON transcripts(call_sid);

CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    district TEXT,
    admin_email TEXT,
    student_count_range TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    role TEXT,
    tenant_id TEXT,
    avatar_seed TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


# ---------------------------------------------------------------------------
# GatewayDB
# ---------------------------------------------------------------------------

class GatewayDB:
    """
    SQLite database manager for the gateway module.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("GATEWAY_DB_PATH", "gateway.db")
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def seed_demo_data(self, tenant_id: str = "lincoln-high") -> None:
        """Seed with demo data matching frontend mock data."""
        with self._connect() as conn:
            # Seed tenant
            conn.execute(
                """INSERT OR IGNORE INTO tenants (tenant_id, name, district, admin_email, student_count_range)
                   VALUES (?, ?, ?, ?, ?)""",
                (tenant_id, "Lincoln High School", "District 12", "admin@school.edu", "1000-1500"),
            )
            # Seed users matching mock-auth.ts
            conn.execute(
                """INSERT OR IGNORE INTO users (email, full_name, role, tenant_id, avatar_seed)
                   VALUES (?, ?, ?, ?, ?)""",
                ("admin@school.edu", "Dr. Sarah Mitchell", "Principal", tenant_id, "Principal"),
            )
            conn.execute(
                """INSERT OR IGNORE INTO users (email, full_name, role, tenant_id, avatar_seed)
                   VALUES (?, ?, ?, ?, ?)""",
                ("teacher@school.edu", "Mr. James Okafor", "Teacher", tenant_id, "Teacher"),
            )
            # Seed students matching frontend mock
            students = [
                (tenant_id, "Emma Thompson", "10th Grade", "Sarah Thompson", "+1 (555) 123-4567", "Present", "Absence (Resolved)"),
                (tenant_id, "James Wilson", "11th Grade", "Michael Wilson", "+1 (555) 987-6543", "Absent", "Fee Reminder (Failed)"),
                (tenant_id, "Sophia Martinez", "9th Grade", "Elena Martinez", "+1 (555) 456-7890", "Present", "Announcement (Delivered)"),
                (tenant_id, "Liam Garcia", "12th Grade", "Maria Garcia", "+1 (555) 234-5678", "Absent", "Absence Follow-up (Active)"),
                (tenant_id, "Olivia Brown", "10th Grade", "David Brown", "+1 (555) 345-6789", "Present", "None"),
            ]
            conn.executemany(
                """INSERT OR IGNORE INTO students
                   (tenant_id, name, grade, parent_name, parent_phone, attendance_status, recent_call_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                students,
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            return self._row_to_user(row) if row else None

    def _row_to_user(self, row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            tenant_id=row["tenant_id"],
            avatar_seed=row["avatar_seed"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )

    # ------------------------------------------------------------------
    # Tenants
    # ------------------------------------------------------------------

    def create_tenant(self, tenant: Tenant) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO tenants (tenant_id, name, district, admin_email, student_count_range)
                   VALUES (?, ?, ?, ?, ?)""",
                (tenant.tenant_id, tenant.name, tenant.district, tenant.admin_email, tenant.student_count_range),
            )
            conn.commit()
            return cursor.lastrowid

    def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
            return self._row_to_tenant(row) if row else None

    def _row_to_tenant(self, row: sqlite3.Row) -> Tenant:
        return Tenant(
            id=row["id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            district=row["district"],
            admin_email=row["admin_email"],
            student_count_range=row["student_count_range"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )

    # ------------------------------------------------------------------
    # Students
    # ------------------------------------------------------------------

    def create_student(self, student: Student) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO students
                   (tenant_id, name, grade, parent_name, parent_phone, attendance_status, recent_call_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (student.tenant_id, student.name, student.grade, student.parent_name,
                 student.parent_phone, student.attendance_status, student.recent_call_summary),
            )
            conn.commit()
            return cursor.lastrowid

    def get_student(self, student_id: int) -> Optional[Student]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
            return self._row_to_student(row) if row else None

    def update_student(self, student_id: int, fields: Dict[str, Any]) -> bool:
        allowed = {"name", "grade", "parent_name", "parent_phone", "attendance_status", "recent_call_summary"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return False
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [student_id]
        with self._connect() as conn:
            cursor = conn.execute(f"UPDATE students SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_student(self, student_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_students(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        grade: Optional[str] = None,
    ) -> tuple[List[Student], int]:
        with self._connect() as conn:
            where_clauses = ["tenant_id = ?"]
            params: List[Any] = [tenant_id]

            if search:
                where_clauses.append(
                    "(name LIKE ? OR parent_name LIKE ? OR parent_phone LIKE ?)"
                )
                like = f"%{search}%"
                params.extend([like, like, like])

            if grade:
                where_clauses.append("grade = ?")
                params.append(grade)

            where_sql = " AND ".join(where_clauses)

            count_row = conn.execute(
                f"SELECT COUNT(*) as c FROM students WHERE {where_sql}", params
            ).fetchone()
            total = count_row["c"] if count_row else 0

            offset = (page - 1) * page_size
            rows = conn.execute(
                f"""SELECT * FROM students WHERE {where_sql}
                    ORDER BY name ASC
                    LIMIT ? OFFSET ?""",
                params + [page_size, offset],
            ).fetchall()

            return [self._row_to_student(r) for r in rows], total

    def _row_to_student(self, row: sqlite3.Row) -> Student:
        return Student(
            id=row["id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            grade=row["grade"],
            parent_name=row["parent_name"],
            parent_phone=row["parent_phone"],
            attendance_status=row["attendance_status"],
            recent_call_summary=row["recent_call_summary"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )

    # ------------------------------------------------------------------
    # Call Logs
    # ------------------------------------------------------------------

    def create_call_log(self, call: CallLog) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO call_logs
                   (call_sid, tenant_id, student_id, domain, direction, phone_to, phone_from, status, call_type, duration_seconds, transcript_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (call.call_sid, call.tenant_id, call.student_id, call.domain, call.direction,
                 call.phone_to, call.phone_from, call.status, call.call_type, call.duration_seconds, call.transcript_summary),
            )
            conn.commit()
            return cursor.lastrowid

    def get_call_log(self, call_log_id: int) -> Optional[CallLog]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM call_logs WHERE id = ?", (call_log_id,)).fetchone()
            return self._row_to_call_log(row) if row else None

    def get_call_log_by_sid(self, call_sid: str) -> Optional[CallLog]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM call_logs WHERE call_sid = ?", (call_sid,)).fetchone()
            return self._row_to_call_log(row) if row else None

    def update_call_log(self, call_sid: str, fields: Dict[str, Any]) -> bool:
        allowed = {"status", "duration_seconds", "transcript_summary", "ended_at", "student_id"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [call_sid]
        with self._connect() as conn:
            cursor = conn.execute(f"UPDATE call_logs SET {set_clause} WHERE call_sid = ?", values)
            conn.commit()
            return cursor.rowcount > 0

    def list_call_logs(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> tuple[List[CallLog], int]:
        with self._connect() as conn:
            where_clauses = ["tenant_id = ?"]
            params: List[Any] = [tenant_id]

            if status:
                where_clauses.append("status = ?")
                params.append(status)

            where_sql = " AND ".join(where_clauses)

            count_row = conn.execute(
                f"SELECT COUNT(*) as c FROM call_logs WHERE {where_sql}", params
            ).fetchone()
            total = count_row["c"] if count_row else 0

            offset = (page - 1) * page_size
            rows = conn.execute(
                f"""SELECT * FROM call_logs WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?""",
                params + [page_size, offset],
            ).fetchall()

            return [self._row_to_call_log(r) for r in rows], total

    def _row_to_call_log(self, row: sqlite3.Row) -> CallLog:
        return CallLog(
            id=row["id"],
            call_sid=row["call_sid"],
            tenant_id=row["tenant_id"],
            student_id=row["student_id"],
            domain=row["domain"],
            direction=row["direction"],
            phone_to=row["phone_to"],
            phone_from=row["phone_from"],
            status=row["status"],
            call_type=row["call_type"],
            duration_seconds=row["duration_seconds"],
            transcript_summary=row["transcript_summary"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
        )

    # ------------------------------------------------------------------
    # Transcripts
    # ------------------------------------------------------------------

    def create_transcript(self, t: TranscriptRow) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO transcripts (call_sid, speaker, text, timestamp_ms)
                   VALUES (?, ?, ?, ?)""",
                (t.call_sid, t.speaker, t.text, t.timestamp_ms),
            )
            conn.commit()
            return cursor.lastrowid

    def get_transcripts_for_call(self, call_sid: str) -> List[TranscriptRow]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM transcripts WHERE call_sid = ? ORDER BY timestamp_ms ASC",
                (call_sid,),
            ).fetchall()
            return [self._row_to_transcript(r) for r in rows]

    def _row_to_transcript(self, row: sqlite3.Row) -> TranscriptRow:
        return TranscriptRow(
            id=row["id"],
            call_sid=row["call_sid"],
            speaker=row["speaker"],
            text=row["text"],
            timestamp_ms=row["timestamp_ms"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )
