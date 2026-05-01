"""
AI Receptionist Data Models
SQLite-backed models for appointments, contractors, and call tasks.
Ref: ADR-005; scheduling theory for conflict-free booking.
"""

import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from enum import Enum
import json

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
    """
    A contractor or staff member who can be scheduled.
    """
    id: Optional[int]
    name: str
    phone: str
    email: str
    specialty: str
    timezone: str = "UTC"
    daily_limit: int = 8  # max appointments per day
    is_active: bool = True
    notes: str = ""

@dataclass
class Appointment:
    """
    A scheduled appointment or call.
    """
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
    """
    A single availability window for a contractor.
    Generated dynamically from contractor templates and existing appointments.
    """
    contractor_id: int
    date: date
    start_time: datetime
    end_time: datetime
    is_available: bool = True

@dataclass
class CallTask:
    """
    An outbound call task to contact a contractor.
    """
    id: Optional[int]
    contractor_id: int
    purpose: str
    scheduled_time: Optional[datetime]
    status: CallTaskStatus
    twilio_call_sid: Optional[str] = None
    result_notes: str = ""
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# ---------------------------------------------------------------------------
# Database Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS contractors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    specialty TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    daily_limit INTEGER DEFAULT 8,
    is_active INTEGER DEFAULT 1,
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER NOT NULL,
    caller_name TEXT NOT NULL,
    caller_phone TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    status TEXT NOT NULL DEFAULT 'scheduled',
    appointment_type TEXT NOT NULL DEFAULT 'in_person',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contractor_id) REFERENCES contractors(id)
);

CREATE INDEX IF NOT EXISTS idx_appointments_contractor_date
    ON appointments(contractor_id, start_time);

CREATE INDEX IF NOT EXISTS idx_appointments_status
    ON appointments(status);

CREATE TABLE IF NOT EXISTS call_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contractor_id INTEGER NOT NULL,
    purpose TEXT NOT NULL,
    scheduled_time TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    twilio_call_sid TEXT,
    result_notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (contractor_id) REFERENCES contractors(id)
);

CREATE INDEX IF NOT EXISTS idx_call_tasks_status
    ON call_tasks(status);

CREATE INDEX IF NOT EXISTS idx_call_tasks_scheduled
    ON call_tasks(scheduled_time);
"""

class Database:
    """
    SQLite database manager for the receptionist.
    Production: swap connection string to PostgreSQL.
    """

    def __init__(self, db_path: str = "receptionist.db"):
        self.db_path = db_path
        self._conn = None
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        # For in-memory DBs, reuse the same connection so tables persist
        if self.db_path == ":memory:":
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA foreign_keys = ON")
            return self._conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        conn.executescript(SCHEMA_SQL)
        if self.db_path != ":memory:":
            conn.close()

    # -----------------------------------------------------------------------
    # Contractors
    # -----------------------------------------------------------------------

    def add_contractor(self, c: Contractor) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO contractors (name, phone, email, specialty, timezone, daily_limit, is_active, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (c.name, c.phone, c.email, c.specialty, c.timezone, c.daily_limit, int(c.is_active), c.notes),
            )
            conn.commit()
            return cursor.lastrowid

    def get_contractor(self, contractor_id: int) -> Optional[Contractor]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM contractors WHERE id = ?", (contractor_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_contractor(row)

    def list_contractors(self, active_only: bool = True) -> List[Contractor]:
        with self._connect() as conn:
            sql = "SELECT * FROM contractors"
            params = ()
            if active_only:
                sql += " WHERE is_active = 1"
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_contractor(r) for r in rows]

    def find_contractors_by_specialty(self, specialty: str) -> List[Contractor]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM contractors WHERE specialty LIKE ? AND is_active = 1",
                (f"%{specialty}%",),
            ).fetchall()
            return [self._row_to_contractor(r) for r in rows]

    def _row_to_contractor(self, row: sqlite3.Row) -> Contractor:
        return Contractor(
            id=row["id"],
            name=row["name"],
            phone=row["phone"],
            email=row["email"],
            specialty=row["specialty"],
            timezone=row["timezone"],
            daily_limit=row["daily_limit"],
            is_active=bool(row["is_active"]),
            notes=row["notes"],
        )

    # -----------------------------------------------------------------------
    # Appointments
    # -----------------------------------------------------------------------

    def add_appointment(self, a: Appointment) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO appointments
                   (contractor_id, caller_name, caller_phone, start_time, duration_minutes, status, appointment_type, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (a.contractor_id, a.caller_name, a.caller_phone,
                 a.start_time.isoformat(), a.duration_minutes, a.status.value,
                 a.appointment_type.value, a.notes),
            )
            conn.commit()
            return cursor.lastrowid

    def get_appointment(self, appointment_id: int) -> Optional[Appointment]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_appointment(row)

    def list_appointments_for_contractor(
        self,
        contractor_id: int,
        start: datetime,
        end: datetime,
        status_filter: Optional[List[AppointmentStatus]] = None,
    ) -> List[Appointment]:
        with self._connect() as conn:
            sql = "SELECT * FROM appointments WHERE contractor_id = ? AND start_time BETWEEN ? AND ?"
            params = (contractor_id, start.isoformat(), end.isoformat())
            if status_filter:
                placeholders = ",".join("?" * len(status_filter))
                sql += f" AND status IN ({placeholders})"
                params += tuple(s.value for s in status_filter)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_appointment(r) for r in rows]

    def cancel_appointment(self, appointment_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (AppointmentStatus.CANCELLED.value, appointment_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_appointment_status(self, appointment_id: int, status: AppointmentStatus) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status.value, appointment_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_appointment(self, row: sqlite3.Row) -> Appointment:
        return Appointment(
            id=row["id"],
            contractor_id=row["contractor_id"],
            caller_name=row["caller_name"],
            caller_phone=row["caller_phone"],
            start_time=datetime.fromisoformat(row["start_time"]),
            duration_minutes=row["duration_minutes"],
            status=AppointmentStatus(row["status"]),
            appointment_type=AppointmentType(row["appointment_type"]),
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )

    # -----------------------------------------------------------------------
    # Call Tasks
    # -----------------------------------------------------------------------

    def add_call_task(self, t: CallTask) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO call_tasks (contractor_id, purpose, scheduled_time, status, twilio_call_sid, result_notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (t.contractor_id, t.purpose,
                 t.scheduled_time.isoformat() if t.scheduled_time else None,
                 t.status.value, t.twilio_call_sid, t.result_notes),
            )
            conn.commit()
            return cursor.lastrowid

    def get_pending_call_tasks(self, before: Optional[datetime] = None) -> List[CallTask]:
        with self._connect() as conn:
            sql = "SELECT * FROM call_tasks WHERE status IN ('pending', 'queued')"
            params = ()
            if before:
                sql += " AND (scheduled_time IS NULL OR scheduled_time <= ?)"
                params = (before.isoformat(),)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_call_task(r) for r in rows]

    def update_call_task_status(self, task_id: int, status: CallTaskStatus, notes: str = "", call_sid: Optional[str] = None) -> bool:
        with self._connect() as conn:
            fields = ["status = ?", "result_notes = ?"]
            params = [status.value, notes]
            if call_sid:
                fields.append("twilio_call_sid = ?")
                params.append(call_sid)
            if status in (CallTaskStatus.COMPLETED, CallTaskStatus.FAILED, CallTaskStatus.CANCELLED):
                fields.append("completed_at = CURRENT_TIMESTAMP")
            params.append(task_id)
            cursor = conn.execute(
                f"UPDATE call_tasks SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_call_task(self, row: sqlite3.Row) -> CallTask:
        return CallTask(
            id=row["id"],
            contractor_id=row["contractor_id"],
            purpose=row["purpose"],
            scheduled_time=datetime.fromisoformat(row["scheduled_time"]) if row["scheduled_time"] else None,
            status=CallTaskStatus(row["status"]),
            twilio_call_sid=row["twilio_call_sid"],
            result_notes=row["result_notes"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

# References
# [^28]: Newman, S. (2015). Building Microservices. O'Reilly. Event sourcing chapter.
# [^46]: American Medical Association. (2021). Optimized Scheduling for Primary Care Practices.
