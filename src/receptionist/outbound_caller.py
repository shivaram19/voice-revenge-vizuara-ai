"""
Outbound Calling System
Manages call tasks to contact contractors automatically.
Ref: Twilio REST API for outbound calls; ADR-005 telephony architecture.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from src.receptionist.models import (
    Database,
    CallTask,
    CallTaskStatus,
    Contractor,
)


class OutboundCaller:
    """
    Outbound calling orchestrator.

    Workflow:
    1. Receptionist or scheduler creates a CallTask (e.g., "call plumber about leak").
    2. OutboundCaller polls pending tasks and initiates Twilio calls.
    3. Contractor answers → connected to a conference or hears a message.
    4. Result recorded back to database.

    Ref: Twilio. (2024). REST API: Making Calls. twilio.com/docs/voice/make-calls.
    """

    def __init__(self, db: Database):
        self.db = db
        self._twilio_client = None  # Initialized when SID/token provided

    def configure_twilio(self, account_sid: str, auth_token: str):
        """Initialize Twilio REST client."""
        try:
            from twilio.rest import Client
            self._twilio_client = Client(account_sid, auth_token)
        except ImportError:
            raise RuntimeError("twilio package not installed. Run: pip install twilio")

    def create_task(
        self,
        contractor_id: int,
        purpose: str,
        scheduled_time: Optional[datetime] = None,
    ) -> int:
        """
        Create a new outbound call task.
        Returns the task ID.
        """
        task = CallTask(
            id=None,
            contractor_id=contractor_id,
            purpose=purpose,
            scheduled_time=scheduled_time,
            status=CallTaskStatus.PENDING,
        )
        return self.db.add_call_task(task)

    def get_due_tasks(self) -> List[CallTask]:
        """
        Get all call tasks that are ready to be executed.
        Tasks with no scheduled_time are due immediately.
        """
        now = datetime.utcnow()
        return self.db.get_pending_call_tasks(before=now)

    def initiate_call(self, task: CallTask, from_number: str, callback_url: str) -> Optional[str]:
        """
        Initiate a Twilio outbound call for a task.
        Returns the Twilio Call SID, or None if failed.

        Args:
            task: The CallTask to execute.
            from_number: The Twilio number to call from.
            callback_url: URL for Twilio status callbacks.
        """
        if not self._twilio_client:
            raise RuntimeError("Twilio client not configured. Call configure_twilio() first.")

        contractor = self.db.get_contractor(task.contractor_id)
        if not contractor:
            self.db.update_call_task_status(task.id, CallTaskStatus.FAILED, "Contractor not found")
            return None

        try:
            call = self._twilio_client.calls.create(
                to=contractor.phone,
                from_=from_number,
                url=callback_url,  # TwiML URL to handle answered call
                status_callback=callback_url + "/status",
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                machine_detection="Enable",
                machine_detection_timeout=10,
            )

            self.db.update_call_task_status(
                task.id,
                CallTaskStatus.DIALING,
                call_sid=call.sid,
            )
            return call.sid

        except Exception as e:
            self.db.update_call_task_status(
                task.id,
                CallTaskStatus.FAILED,
                notes=str(e),
            )
            return None

    def handle_status_callback(self, task_id: int, call_sid: str, call_status: str, call_duration: int = 0) -> None:
        """
        Handle Twilio status callback for an outbound call.
        Updates task status based on call outcome.
        """
        status_map = {
            "queued": CallTaskStatus.QUEUED,
            "ringing": CallTaskStatus.DIALING,
            "in-progress": CallTaskStatus.CONNECTED,
            "completed": CallTaskStatus.COMPLETED,
            "busy": CallTaskStatus.FAILED,
            "failed": CallTaskStatus.FAILED,
            "no-answer": CallTaskStatus.FAILED,
            "canceled": CallTaskStatus.CANCELLED,
        }

        new_status = status_map.get(call_status, CallTaskStatus.FAILED)
        notes = f"Call status: {call_status}"
        if call_duration > 0:
            notes += f", Duration: {call_duration}s"

        self.db.update_call_task_status(task_id, new_status, notes=notes, call_sid=call_sid)

    def format_task_summary(self, task: CallTask) -> str:
        """Format a call task for voice notification to receptionist."""
        contractor = self.db.get_contractor(task.contractor_id)
        name = contractor.name if contractor else "Unknown contractor"

        if task.status == CallTaskStatus.COMPLETED:
            return f"Call to {name} completed. {task.result_notes}"
        elif task.status == CallTaskStatus.FAILED:
            return f"Call to {name} failed. {task.result_notes}"
        elif task.status == CallTaskStatus.DIALING:
            return f"Calling {name} now..."
        else:
            return f"Call to {name} is {task.status.value}."


# References
# [^43]: Twilio. (2024). Call Status Callbacks. twilio.com/docs/voice/api/call-resource#statuscallback.
