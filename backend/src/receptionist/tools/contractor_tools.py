"""
Contractor & Scheduling Tools for AI Receptionist
Replaces simple calendar with real contractor management.
Ref: OpenAI Function Calling API [^13]; ADR-005.
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple

from src.receptionist.models import Database, Contractor, Appointment, AppointmentType, AppointmentStatus, CallTask
from src.receptionist.scheduler import SchedulingEngine
from src.receptionist.outbound_caller import OutboundCaller


@dataclass
class BookingResult:
    success: bool
    message: str
    appointment_id: Optional[int] = None


class ContractorDirectory:
    """
    Manages contractor lookup and scheduling.
    Production: integrate with HR/contractor management system.
    """

    def __init__(self, db: Database):
        self.db = db
        self.scheduler = SchedulingEngine(db)

    async def find_contractors(self, query: str) -> List[Contractor]:
        """Search contractors by name, specialty, or phone."""
        query_lower = query.lower()
        all_contractors = await self.db.list_contractors(active_only=True)
        scored = []

        for c in all_contractors:
            score = 0
            fields = [c.name.lower(), c.specialty.lower(), c.phone]
            for field in fields:
                if query_lower in field:
                    score += 2 if query_lower == field else 1
            if score > 0:
                scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:3]]

    async def check_availability(
        self,
        contractor_id: int,
        target_date: date,
        duration_minutes: int = 30,
    ) -> List[datetime]:
        """Return available start times for a contractor on a date."""
        slots = await self.scheduler.get_available_slots(
            contractor_id=contractor_id,
            target_date=target_date,
            duration_minutes=duration_minutes,
        )
        return [s.start_time for s in slots]

    async def book_appointment(
        self,
        contractor_id: int,
        caller_name: str,
        caller_phone: str,
        start_time: datetime,
        duration_minutes: int = 30,
        appointment_type: AppointmentType = AppointmentType.IN_PERSON,
        notes: str = "",
    ) -> BookingResult:
        """Book an appointment with a contractor."""
        success, message, appt_id = await self.scheduler.book_appointment(
            contractor_id=contractor_id,
            caller_name=caller_name,
            caller_phone=caller_phone,
            start_time=start_time,
            duration_minutes=duration_minutes,
            appointment_type=appointment_type,
            notes=notes,
        )
        return BookingResult(success=success, message=message, appointment_id=appt_id)

    async def cancel_appointment(self, appointment_id: int) -> Tuple[bool, str]:
        """Cancel an existing appointment."""
        return await self.scheduler.cancel_appointment(appointment_id)

    async def reschedule_appointment(
        self,
        appointment_id: int,
        new_start_time: datetime,
    ) -> Tuple[bool, str, Optional[int]]:
        """Reschedule an appointment."""
        return await self.scheduler.reschedule_appointment(appointment_id, new_start_time)

    async def get_schedule(self, contractor_id: int, start_date: date, end_date: date) -> List[Appointment]:
        """Get a contractor's schedule."""
        return await self.scheduler.get_contractor_schedule(contractor_id, start_date, end_date)

    def format_for_voice(self, contractors: List[Contractor]) -> str:
        """Format contractor list for spoken response."""
        if not contractors:
            return "I couldn't find anyone matching that description."
        if len(contractors) == 1:
            c = contractors[0]
            return f"I found {c.name}, {c.specialty}. Their number is {self._format_phone(c.phone)}."
        lines = ["I found a few matches:"]
        for c in contractors:
            lines.append(f"{c.name}, {c.specialty}.")
        return " ".join(lines)

    async def format_appointment_for_voice(self, appt: Appointment) -> str:
        """Format appointment confirmation for spoken response."""
        contractor = await self.db.get_contractor(appt.contractor_id)
        name = contractor.name if contractor else "your contractor"
        time_str = appt.start_time.strftime("%I:%M %p")
        date_str = appt.start_time.strftime("%A, %B %d")
        type_str = "phone call" if appt.appointment_type == AppointmentType.PHONE else "in-person visit"
        return f"Your {type_str} with {name} is scheduled for {time_str} on {date_str}."

    @staticmethod
    def _format_phone(phone: str) -> str:
        """Format phone number for speech."""
        if len(phone) == 10:
            return f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
        if len(phone) == 11 and phone.startswith("1"):
            return f"{phone[1:4]}-{phone[4:7]}-{phone[7:]}"
        return phone


class OutboundCallManager:
    """
    Manages outbound calls to contractors.
    Wraps OutboundCaller with voice-friendly formatting.
    """

    def __init__(self, db: Database):
        self.db = db
        self.caller = OutboundCaller(db)

    async def schedule_call_to_contractor(
        self,
        contractor_id: int,
        purpose: str,
        scheduled_time: Optional[datetime] = None,
    ) -> Tuple[bool, str, int]:
        """
        Schedule an outbound call to a contractor.
        Returns (success, message, task_id).
        """
        contractor = await self.db.get_contractor(contractor_id)
        if not contractor:
            return False, "Contractor not found.", -1

        task_id = await self.caller.create_task(
            contractor_id=contractor_id,
            purpose=purpose,
            scheduled_time=scheduled_time,
        )

        if scheduled_time:
            time_str = scheduled_time.strftime("%I:%M %p")
            date_str = scheduled_time.strftime("%A, %B %d")
            return True, f"I'll call {contractor.name} at {time_str} on {date_str} about: {purpose}.", task_id
        else:
            return True, f"I'll call {contractor.name} right now about: {purpose}.", task_id

    async def get_pending_calls(self) -> List[CallTask]:
        """Get all pending outbound call tasks."""
        return await self.caller.get_due_tasks()

    def format_call_status_for_voice(self, task_id: int) -> str:
        """Format call task status for spoken response."""
        # This would query the DB for the task; simplified here
        return "Call status requested."


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
