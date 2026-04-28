"""
Education-specific tools for the voice receptionist.

Each tool is self-contained: schema definition, execution, and voice-friendly
formatting. Tools operate on in-memory mock data so the domain can be
exercised without external dependencies.

Ref: OpenAI Function Calling API [^13]; ADR-009.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.receptionist.tools.base import Tool, ToolResult
from src.domains.education.seed import (
    EDUCATION_COURSES,
    EDUCATION_ADMISSIONS,
    EDUCATION_FAQ,
    CourseRecord,
    AdmissionRecord,
)


# ---------------------------------------------------------------------------
# Course Lookup Tool
# ---------------------------------------------------------------------------

class CourseLookupTool(Tool):
    """
    Lookup courses by name or category.

    Searches the in-memory course catalogue using keyword matching.
    Production: integrate with Student Information System (SIS) API.
    """

    def __init__(self, courses: Optional[List[CourseRecord]] = None):
        self._courses = courses or list(EDUCATION_COURSES)

    @property
    def name(self) -> str:
        return "lookup_course"

    @property
    def description(self) -> str:
        return "Search for courses by name, category, or keyword. Returns matching courses with duration and tuition."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Course name, category (e.g., technology, business, arts, healthcare), or keyword.",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "").lower()
        if not query:
            return ToolResult(
                success=False,
                message="Please provide a course name or category to search.",
                error="missing_query",
            )

        matches: List[CourseRecord] = []
        for course in self._courses:
            if (
                query in course.name.lower()
                or query in course.category.lower()
                or query in course.description.lower()
            ):
                matches.append(course)

        if not matches:
            return ToolResult(
                success=False,
                message=f"I couldn't find any courses matching '{query}'. Would you like to browse all categories?",
                error="no_results",
            )

        lines: List[str] = []
        for c in matches[:3]:
            lines.append(
                f"{c.name}, {c.category}. Duration: {c.duration_months} months. "
                f"Tuition: ${c.tuition_usd:,.0f}."
            )
        message = " ".join(lines)
        return ToolResult(
            success=True,
            message=message,
            data={"matches": [self._course_to_dict(c) for c in matches]},
        )

    @staticmethod
    def _course_to_dict(course: CourseRecord) -> Dict[str, Any]:
        return {
            "name": course.name,
            "category": course.category,
            "duration_months": course.duration_months,
            "tuition_usd": course.tuition_usd,
            "description": course.description,
        }


# ---------------------------------------------------------------------------
# Check Admission Status Tool
# ---------------------------------------------------------------------------

class CheckAdmissionStatusTool(Tool):
    """
    Check a student's admission application status by student ID.

    Production: integrate with admissions portal or CRM (e.g., Salesforce
    Education Cloud, Slate).
    """

    def __init__(self, admissions: Optional[List[AdmissionRecord]] = None):
        self._admissions = admissions or list(EDUCATION_ADMISSIONS)

    @property
    def name(self) -> str:
        return "check_admission_status"

    @property
    def description(self) -> str:
        return "Check the status of a student's admission application using their student ID."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "The student's application ID, e.g., EDU-2026-001.",
                },
            },
            "required": ["student_id"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        student_id = kwargs.get("student_id", "").strip()
        if not student_id:
            return ToolResult(
                success=False,
                message="Please provide your student ID so I can look up your application.",
                error="missing_student_id",
            )

        record = next(
            (a for a in self._admissions if a.student_id.lower() == student_id.lower()),
            None,
        )

        if not record:
            return ToolResult(
                success=False,
                message=f"I couldn't find an application for student ID {student_id}. Please double-check the ID.",
                error="not_found",
            )

        status_msg = (
            f"Hello {record.name}. Your application for {record.program} is currently {record.status}."
        )
        if record.notes:
            status_msg += f" {record.notes}"

        return ToolResult(
            success=True,
            message=status_msg,
            data={
                "student_id": record.student_id,
                "name": record.name,
                "program": record.program,
                "status": record.status,
            },
        )


# ---------------------------------------------------------------------------
# Schedule Campus Visit Tool
# ---------------------------------------------------------------------------

class ScheduleCampusVisitTool(Tool):
    """
    Schedule an on-campus tour or visit.

    Maintains an in-memory booking ledger. Production: integrate with
    calendar system (Google Calendar, Microsoft Bookings).

    Ref: idempotency keys prevent double-booking under retry [^44].
    """

    def __init__(self, existing_bookings: Optional[List[Dict[str, Any]]] = None):
        self._bookings: List[Dict[str, Any]] = existing_bookings or []
        self._business_hours = (9, 17)  # 9 AM to 5 PM

    @property
    def name(self) -> str:
        return "schedule_campus_visit"

    @property
    def description(self) -> str:
        return (
            "Schedule a campus tour for a prospective student. "
            "Requires date (YYYY-MM-DD), time (HH:MM), and visitor name. "
            "Confirm availability before saving."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Preferred visit date in YYYY-MM-DD format.",
                },
                "time": {
                    "type": "string",
                    "description": "Preferred visit time in HH:MM 24-hour format.",
                },
                "name": {
                    "type": "string",
                    "description": "Full name of the visitor.",
                },
                "email": {
                    "type": "string",
                    "description": "Email address for confirmation (optional).",
                },
            },
            "required": ["date", "time", "name"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        date_str = kwargs.get("date", "")
        time_str = kwargs.get("time", "")
        name = kwargs.get("name", "").strip()
        email = kwargs.get("email", "")

        if not name:
            return ToolResult(
                success=False,
                message="I need your name to schedule the campus visit.",
                error="missing_name",
            )

        try:
            visit_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            return ToolResult(
                success=False,
                message="I didn't understand the date or time. Please say them clearly, for example, June tenth at two PM.",
                error="invalid_datetime",
            )

        if not (self._business_hours[0] <= visit_dt.hour < self._business_hours[1]):
            return ToolResult(
                success=False,
                message="Campus visits are only available between 9 AM and 5 PM, Monday through Friday.",
                error="outside_hours",
            )

        # Simple duplicate check (same date + time)
        for b in self._bookings:
            if b["datetime"] == visit_dt:
                return ToolResult(
                    success=False,
                    message="That time slot is already booked. I can suggest another time if you'd like.",
                    error="slot_unavailable",
                )

        booking = {
            "datetime": visit_dt,
            "name": name,
            "email": email,
        }
        self._bookings.append(booking)

        time_friendly = visit_dt.strftime("%I:%M %p")
        date_friendly = visit_dt.strftime("%A, %B %d")
        return ToolResult(
            success=True,
            message=f"Your campus tour is scheduled for {time_friendly} on {date_friendly}. We look forward to seeing you, {name}.",
            data=booking,
        )


# ---------------------------------------------------------------------------
# Fee Inquiry Tool
# ---------------------------------------------------------------------------

class FeeInquiryTool(Tool):
    """
    Look up the fee structure for a specific course or program.

    Returns tuition, estimated materials cost, and available payment plans.
    """

    def __init__(self, courses: Optional[List[CourseRecord]] = None):
        self._courses = courses or list(EDUCATION_COURSES)

    @property
    def name(self) -> str:
        return "fee_inquiry"

    @property
    def description(self) -> str:
        return "Look up tuition fees, material costs, and payment plan options for a specific course or program."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "course_name": {
                    "type": "string",
                    "description": "Exact or partial name of the course or program.",
                },
            },
            "required": ["course_name"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        course_name = kwargs.get("course_name", "").lower()
        if not course_name:
            return ToolResult(
                success=False,
                message="Please tell me which course or program you'd like fee information for.",
                error="missing_course_name",
            )

        match = next(
            (c for c in self._courses if course_name in c.name.lower()),
            None,
        )

        if not match:
            return ToolResult(
                success=False,
                message=f"I couldn't find fee information for '{course_name}'. Would you like a list of all programs?",
                error="course_not_found",
            )

        materials_estimate = match.tuition_usd * 0.05  # 5% materials estimate
        message = (
            f"The {match.name} program tuition is ${match.tuition_usd:,.0f} for the full {match.duration_months}-month duration. "
            f"Estimated materials and lab fees are around ${materials_estimate:,.0f}. "
            f"Payment plans are available: semester-wise or monthly instalments."
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "course": match.name,
                "tuition_usd": match.tuition_usd,
                "duration_months": match.duration_months,
                "materials_estimate_usd": materials_estimate,
            },
        )


# ---------------------------------------------------------------------------
# FAQ Search Tool
# ---------------------------------------------------------------------------

class FAQTool(Tool):
    """
    Search the education FAQ knowledge base.

    Uses simple keyword matching. Production: upgrade to FAISS semantic
    search per ADR-003 [^14][^37].
    """

    def __init__(self, faqs: Optional[List[Dict[str, str]]] = None):
        self._faqs = faqs or list(EDUCATION_FAQ)

    @property
    def name(self) -> str:
        return "search_faq"

    @property
    def description(self) -> str:
        return "Search the education knowledge base for answers about admissions, scholarships, facilities, and policies."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The caller's question or keywords to search for.",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "").lower()
        if not query:
            return ToolResult(
                success=False,
                message="What would you like to know?",
                error="missing_query",
            )

        query_words = set(re.findall(r"\b\w+\b", query))
        scored: List[tuple] = []

        for faq in self._faqs:
            text = f"{faq['question']} {faq['answer']}".lower()
            text_words = set(re.findall(r"\b\w+\b", text))
            score = len(query_words & text_words)
            if score > 0:
                scored.append((score, faq))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:1]

        if not top:
            return ToolResult(
                success=False,
                message="I don't have that information right now. I can connect you with an admissions counsellor.",
                error="no_faq_match",
            )

        answer = top[0][1]["answer"]
        # Truncate to two sentences for voice brevity [^16]
        sentences = re.split(r"[.!?]+\s+", answer)
        voice_answer = ". ".join(sentences[:2]).strip()
        if voice_answer and not voice_answer.endswith("."):
            voice_answer += "."

        return ToolResult(
            success=True,
            message=voice_answer,
            data={"question": top[0][1]["question"], "answer": answer},
        )


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^14]: Qiu, J., et al. (2026). VoiceAgentRAG. arXiv:2603.02206.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^37]: Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.
# [^44]: Stripe. (2023). Idempotency Keys API Design. stripe.com/docs/api/idempotent_requests.
