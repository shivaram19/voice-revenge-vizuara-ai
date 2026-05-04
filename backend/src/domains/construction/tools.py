"""
Construction-specific tools for the voice agent domain.
OCP: tools are registered, not hardcoded.
Ref: OpenAI (2023). Function Calling API [^13].
"""

from datetime import datetime
from typing import Dict, Any

from src.receptionist.tools.base import Tool, ToolResult
from src.receptionist.models import Database, AppointmentType
from src.receptionist.scheduler import SchedulingEngine
from src.receptionist.tools.faq import FAQKnowledgeBase


class FindContractorTool(Tool):
    """Find a contractor by specialty or name."""

    def __init__(self, db: Database):
        self.db = db

    @property
    def name(self) -> str:
        return "find_contractor"

    @property
    def description(self) -> str:
        return "Find a contractor by specialty or name."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"properties": {"query": {"type": "string"}}, "required": ["query"]}

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        all_contractors = await self.db.list_contractors(active_only=True)
        query_lower = query.lower()
        results = [
            c
            for c in all_contractors
            if query_lower in c.specialty.lower()
            or query_lower in c.name.lower()
            or query_lower in c.phone
        ]
        if not results:
            return ToolResult(success=False, message=f"No contractors found for '{query}'.")
        lines = [f"{c.name}, {c.specialty}, phone {c.phone}" for c in results]
        return ToolResult(
            success=True,
            message=f"Found {len(results)} contractor(s): {'; '.join(lines)}.",
            data={
                "contractors": [
                    {"name": c.name, "specialty": c.specialty, "phone": c.phone}
                    for c in results
                ]
            },
        )


class CheckAvailabilityTool(Tool):
    """Check available appointment slots for a contractor on a given date."""

    def __init__(self, db: Database):
        self.db = db
        self.scheduler = SchedulingEngine(db)

    @property
    def name(self) -> str:
        return "check_availability"

    @property
    def description(self) -> str:
        return "Check available appointment slots for a contractor on a given date."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "contractor_id": {"type": "integer"},
                "date": {"type": "string"},
            },
            "required": ["contractor_id", "date"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            cid = int(kwargs["contractor_id"])
            target = datetime.strptime(kwargs["date"], "%Y-%m-%d").date()
        except Exception as e:
            return ToolResult(success=False, message="Invalid parameters.", error=str(e))
        slots = await self.scheduler.get_available_slots(cid, target)
        if not slots:
            return ToolResult(success=False, message="No available slots.")
        times = [s.start_time.strftime("%I:%M %p") for s in slots[:5]]
        return ToolResult(
            success=True,
            message=f"Available times: {', '.join(times)}.",
            data={"slots": times},
        )


class BookAppointmentTool(Tool):
    """Book an appointment with a contractor."""

    def __init__(self, db: Database):
        self.db = db
        self.scheduler = SchedulingEngine(db)

    @property
    def name(self) -> str:
        return "book_appointment"

    @property
    def description(self) -> str:
        return "Book an appointment with a contractor."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "contractor_id": {"type": "integer"},
                "date": {"type": "string"},
                "time": {"type": "string"},
                "caller_name": {"type": "string"},
                "caller_phone": {"type": "string"},
                "duration_minutes": {"type": "integer", "default": 30},
                "notes": {"type": "string", "default": ""},
            },
            "required": ["contractor_id", "date", "time", "caller_name", "caller_phone"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            cid = int(kwargs["contractor_id"])
            target_date = datetime.strptime(kwargs["date"], "%Y-%m-%d").date()
            target_time = datetime.strptime(kwargs["time"], "%H:%M").time()
            start = datetime.combine(target_date, target_time)
            duration = int(kwargs.get("duration_minutes", 30))
            success, msg, appt_id = await self.scheduler.book_appointment(
                cid,
                kwargs["caller_name"],
                kwargs["caller_phone"],
                start,
                duration,
                appointment_type=AppointmentType.IN_PERSON,
                notes=kwargs.get("notes", ""),
            )
        except Exception as e:
            return ToolResult(success=False, message="Invalid booking.", error=str(e))
        return ToolResult(success=success, message=msg, data={"appointment_id": appt_id})


class FAQTool(Tool):
    """Search the company FAQ."""

    def __init__(self, faq_kb: FAQKnowledgeBase):
        self.faq = faq_kb

    @property
    def name(self) -> str:
        return "search_faq"

    @property
    def description(self) -> str:
        return "Search the company FAQ."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"properties": {"query": {"type": "string"}}, "required": ["query"]}

    async def execute(self, **kwargs) -> ToolResult:
        results = self.faq.search(kwargs.get("query", ""), top_k=2)
        if not results:
            return ToolResult(success=False, message="I don't have information on that.")
        text = " ".join(r.text for r in results)
        return ToolResult(success=True, message=text, data={"matches": [r.text for r in results]})


class OutboundCallTool(Tool):
    """Schedule an outbound call to a contractor."""

    def __init__(self, db: Database):
        self.db = db

    @property
    def name(self) -> str:
        return "schedule_outbound_call"

    @property
    def description(self) -> str:
        return "Schedule an outbound call to a contractor."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "contractor_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["contractor_id", "reason"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        cid = int(kwargs.get("contractor_id", 0))
        reason = kwargs.get("reason", "")
        c = await self.db.get_contractor(cid)
        if not c:
            return ToolResult(success=False, message="Contractor not found.")
        return ToolResult(
            success=True,
            message=f"I've scheduled a call to {c.name} at {c.phone} regarding: {reason}.",
        )


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
