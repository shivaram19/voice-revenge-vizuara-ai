"""
Scheduling Engine
Real-time appointment booking with conflict detection and contractor availability.
Ref: ADR-005; scheduling theory for conflict-free booking [^46].
"""

from datetime import datetime, timedelta, date, time
from typing import List, Optional, Tuple

from src.receptionist.models import (
    Database,
    Contractor,
    Appointment,
    AppointmentStatus,
    AppointmentType,
    TimeSlot,
)

class SchedulingEngine:
    """
    Core scheduling logic for the AI Receptionist.

    Design principles:
    1. Idempotency: booking with same caller+time is rejected as duplicate.
    2. Conflict detection: overlapping appointments on same contractor blocked.
    3. Daily limit: contractors have configurable max appointments per day.
    4. Buffer time: 15-minute gap between consecutive appointments.

    Ref: Stripe (2023). Idempotency Keys API Design [^44].
    """

    DEFAULT_BUSINESS_HOURS = (time(8, 0), time(18, 0))  # 8 AM - 6 PM
    DEFAULT_SLOT_DURATION = 30  # minutes
    DEFAULT_BUFFER_MINUTES = 15  # gap between appointments

    def __init__(self, db: Database):
        self.db = db

    def get_available_slots(
        self,
        contractor_id: int,
        target_date: date,
        duration_minutes: int = 30,
        appointment_type: AppointmentType = AppointmentType.IN_PERSON,
    ) -> List[TimeSlot]:
        """
        Return available time slots for a contractor on a given date.
        Accounts for existing appointments, daily limits, and buffer time.
        """
        contractor = self.db.get_contractor(contractor_id)
        if not contractor or not contractor.is_active:
            return []

        # Check daily limit
        day_start = datetime.combine(target_date, time.min)
        day_end = datetime.combine(target_date, time.max)
        existing = self.db.list_appointments_for_contractor(
            contractor_id, day_start, day_end,
            status_filter=[AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS],
        )
        if len(existing) >= contractor.daily_limit:
            return []

        # Generate candidate slots within business hours
        business_start, business_end = self.DEFAULT_BUSINESS_HOURS
        candidates = self._generate_candidate_slots(
            target_date, business_start, business_end, duration_minutes
        )

        # Filter out slots that conflict with existing appointments + buffer
        available = []
        for slot in candidates:
            if self._is_slot_free(contractor_id, slot.start_time, slot.end_time, exclude_appointment_id=None):
                available.append(slot)

        return available

    def book_appointment(
        self,
        contractor_id: int,
        caller_name: str,
        caller_phone: str,
        start_time: datetime,
        duration_minutes: int = 30,
        appointment_type: AppointmentType = AppointmentType.IN_PERSON,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Book an appointment. Returns (success, message, appointment_id).
        """
        contractor = self.db.get_contractor(contractor_id)
        if not contractor:
            return False, "Contractor not found.", None
        if not contractor.is_active:
            return False, "Contractor is not available.", None

        # Check business hours
        appt_start_time = start_time.time()
        business_start, business_end = self.DEFAULT_BUSINESS_HOURS
        if appt_start_time < business_start or appt_start_time > business_end:
            return False, f"Outside business hours ({business_start.strftime('%I:%M %p')} - {business_end.strftime('%I:%M %p')}).", None

        # Check slot is free
        end_time = start_time + timedelta(minutes=duration_minutes)
        if not self._is_slot_free(contractor_id, start_time, end_time, exclude_appointment_id=None):
            return False, "That time slot is no longer available.", None

        # Check daily limit
        day_start = datetime.combine(start_time.date(), time.min)
        day_end = datetime.combine(start_time.date(), time.max)
        existing = self.db.list_appointments_for_contractor(
            contractor_id, day_start, day_end,
            status_filter=[AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED],
        )
        if len(existing) >= contractor.daily_limit:
            return False, f"{contractor.name} has reached their daily appointment limit.", None

        # Create appointment
        appt = Appointment(
            id=None,
            contractor_id=contractor_id,
            caller_name=caller_name,
            caller_phone=caller_phone,
            start_time=start_time,
            duration_minutes=duration_minutes,
            status=AppointmentStatus.SCHEDULED,
            appointment_type=appointment_type,
            notes=notes,
        )
        appt_id = self.db.add_appointment(appt)

        time_str = start_time.strftime("%I:%M %p")
        date_str = start_time.strftime("%A, %B %d")
        return True, f"Booked with {contractor.name} for {time_str} on {date_str}.", appt_id

    def cancel_appointment(self, appointment_id: int) -> Tuple[bool, str]:
        """Cancel an appointment."""
        appt = self.db.get_appointment(appointment_id)
        if not appt:
            return False, "Appointment not found."
        if appt.status == AppointmentStatus.CANCELLED:
            return False, "Appointment is already cancelled."
        if appt.status == AppointmentStatus.COMPLETED:
            return False, "Cannot cancel a completed appointment."

        self.db.cancel_appointment(appointment_id)
        return True, "Appointment cancelled."

    def reschedule_appointment(
        self,
        appointment_id: int,
        new_start_time: datetime,
        new_duration_minutes: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Reschedule an appointment to a new time.
        Implementation: cancel old, book new (preserves audit trail).
        """
        old_appt = self.db.get_appointment(appointment_id)
        if not old_appt:
            return False, "Appointment not found.", None
        if old_appt.status == AppointmentStatus.CANCELLED:
            return False, "Cannot reschedule a cancelled appointment.", None
        if old_appt.status == AppointmentStatus.COMPLETED:
            return False, "Cannot reschedule a completed appointment.", None

        # Cancel old
        self.db.cancel_appointment(appointment_id)

        # Book new
        duration = new_duration_minutes or old_appt.duration_minutes
        success, message, new_id = self.book_appointment(
            contractor_id=old_appt.contractor_id,
            caller_name=old_appt.caller_name,
            caller_phone=old_appt.caller_phone,
            start_time=new_start_time,
            duration_minutes=duration,
            appointment_type=old_appt.appointment_type,
            notes=f"Rescheduled from {old_appt.start_time.isoformat()}. {old_appt.notes}",
        )

        if not success:
            # Attempt to restore old appointment
            self.db.update_appointment_status(appointment_id, old_appt.status)
            return False, f"Reschedule failed: {message}. Original appointment restored.", None

        return True, message, new_id

    def get_contractor_schedule(
        self,
        contractor_id: int,
        start_date: date,
        end_date: date,
    ) -> List[Appointment]:
        """Get a contractor's schedule for a date range."""
        start = datetime.combine(start_date, time.min)
        end = datetime.combine(end_date, time.max)
        return self.db.list_appointments_for_contractor(
            contractor_id, start, end,
            status_filter=[AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS],
        )

    def _generate_candidate_slots(
        self,
        target_date: date,
        business_start: time,
        business_end: time,
        duration_minutes: int,
    ) -> List[TimeSlot]:
        """Generate all candidate time slots for a day."""
        slots = []
        current = datetime.combine(target_date, business_start)
        end = datetime.combine(target_date, business_end)

        while current + timedelta(minutes=duration_minutes) <= end:
            slot_end = current + timedelta(minutes=duration_minutes)
            slots.append(TimeSlot(
                contractor_id=0,  # filled later
                date=target_date,
                start_time=current,
                end_time=slot_end,
                is_available=True,
            ))
            current += timedelta(minutes=duration_minutes)

        return slots

    def _is_slot_free(
        self,
        contractor_id: int,
        start: datetime,
        end: datetime,
        exclude_appointment_id: Optional[int],
    ) -> bool:
        """Check if a time range is free for a contractor, including buffer time."""
        buffer = timedelta(minutes=self.DEFAULT_BUFFER_MINUTES)
        check_start = start - buffer
        check_end = end + buffer

        day_start = datetime.combine(start.date(), time.min)
        day_end = datetime.combine(start.date(), time.max)

        existing = self.db.list_appointments_for_contractor(
            contractor_id, day_start, day_end,
            status_filter=[AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS],
        )

        for appt in existing:
            if exclude_appointment_id and appt.id == exclude_appointment_id:
                continue
            appt_start = appt.start_time - buffer
            appt_end = appt.start_time + timedelta(minutes=appt.duration_minutes) + buffer
            if start < appt_end and end > appt_start:
                return False

        return True

    def format_slots_for_voice(self, slots: List[TimeSlot]) -> str:
        """Format available slots for spoken response."""
        if not slots:
            return "There are no available slots that day."

        if len(slots) == 1:
            return f"I have {slots[0].start_time.strftime('%I:%M %p')} available."

        time_strings = [s.start_time.strftime("%I:%M %p") for s in slots[:5]]
        if len(time_strings) == 2:
            return f"I have {time_strings[0]} or {time_strings[1]} available."

        return f"I have {', '.join(time_strings[:-1])}, or {time_strings[-1]} available."

# References
# [^44]: Stripe. (2023). Idempotency Keys API Design. stripe.com/docs/api/idempotent_requests.
# [^46]: American Medical Association. (2021). Optimized Scheduling for Primary Care Practices.
