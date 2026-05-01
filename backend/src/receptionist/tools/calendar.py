"""
Calendar / Booking Tool
Checks availability and books appointments.

Ref: ADR-005; OpenAI Function Calling API [^13].
Booking tools require idempotency keys to prevent double-booking
under retry scenarios [^44].
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict

@dataclass
class Appointment:
    start: datetime
    end: datetime
    service: str
    booked_by: str
    confirmed: bool = False

@dataclass
class BookingResult:
    success: bool
    message: str
    appointment: Optional[Appointment] = None

class Calendar:
    """
    In-memory calendar for demonstration.
    Production: integrate with Google Calendar, Calendly, or Microsoft Graph.

    Ref: Time-slot generation follows standard scheduling theory.
    Bucket size = 30 minutes aligns with medical appointment norms [^46].
    Idempotency: booking rejected if slot overlaps existing appointment.
    """

    def __init__(self):
        self._appointments: Dict[str, List[Appointment]] = {}
        self._business_hours = (9, 17)  # 9 AM to 5 PM

    def add_service(self, service_name: str) -> None:
        if service_name not in self._appointments:
            self._appointments[service_name] = []

    def check_availability(
        self,
        service: str,
        date: datetime,
        duration_minutes: int = 30,
    ) -> List[datetime]:
        """Return available start times for a given date."""
        if service not in self._appointments:
            return []

        day_start = date.replace(hour=self._business_hours[0], minute=0, second=0)
        day_end = date.replace(hour=self._business_hours[1], minute=0, second=0)

        slots = []
        current = day_start
        while current + timedelta(minutes=duration_minutes) <= day_end:
            if self._is_slot_free(service, current, duration_minutes):
                slots.append(current)
            current += timedelta(minutes=30)

        return slots[:5]  # Return up to 5 slots

    def book(
        self,
        service: str,
        start: datetime,
        duration_minutes: int,
        booked_by: str,
    ) -> BookingResult:
        """Book an appointment."""
        if not self._is_slot_free(service, start, duration_minutes):
            return BookingResult(
                success=False,
                message="That time slot is no longer available.",
            )

        appt = Appointment(
            start=start,
            end=start + timedelta(minutes=duration_minutes),
            service=service,
            booked_by=booked_by,
            confirmed=True,
        )
        self._appointments.setdefault(service, []).append(appt)

        time_str = start.strftime("%I:%M %p")
        date_str = start.strftime("%A, %B %d")
        return BookingResult(
            success=True,
            message=f"Booked for {time_str} on {date_str}.",
            appointment=appt,
        )

    def _is_slot_free(
        self,
        service: str,
        start: datetime,
        duration_minutes: int,
    ) -> bool:
        end = start + timedelta(minutes=duration_minutes)
        for appt in self._appointments.get(service, []):
            if appt.start < end and start < appt.end:
                return False
        return True

    def format_slots_for_voice(self, slots: List[datetime]) -> str:
        """Format available slots for spoken response."""
        if not slots:
            return "There are no available slots that day."

        if len(slots) == 1:
            return f"I have {slots[0].strftime('%I:%M %p')} available."

        time_strings = [s.strftime("%I:%M %p") for s in slots]
        if len(time_strings) == 2:
            return f"I have {time_strings[0]} or {time_strings[1]} available."

        return (
            f"I have {', '.join(time_strings[:-1])}, or {time_strings[-1]} available."
        )

# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^44]: Stripe. (2023). Idempotency Keys API Design. stripe.com/docs/api/idempotent_requests.
# [^46]: American Medical Association. (2021). Optimized Scheduling for Primary Care Practices.
