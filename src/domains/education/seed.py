"""
Education domain seed data and database initializer.

Provides sample FAQ entries, course catalogues, and admissions records
for demonstration and integration testing. All data is in-memory;
production deployments swap this for a real persistence layer.

Ref: SigArch 2026 [^16]; OpenAI Function Calling API [^13].
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class CourseRecord:
    """A single course entry in the education catalogue."""
    name: str
    category: str
    duration_months: int
    tuition_usd: float
    description: str
    prerequisites: List[str]


@dataclass
class AdmissionRecord:
    """A single student admission application."""
    student_id: str
    name: str
    program: str
    status: str  # e.g., "pending", "accepted", "rejected", "waitlisted"
    submitted_date: str
    decision_date: str
    notes: str


# ---------------------------------------------------------------------------
# Sample FAQ entries
# ---------------------------------------------------------------------------

EDUCATION_FAQ: List[Dict[str, str]] = [
    {
        "question": "What are the admission deadlines?",
        "answer": (
            "Fall semester applications close on July 15. "
            "Spring semester applications close on November 30. "
            "Late applications are reviewed on a space-available basis."
        ),
        "category": "admissions",
    },
    {
        "question": "Do you offer scholarships?",
        "answer": (
            "Yes. Merit scholarships cover up to 50 percent of tuition. "
            "Need-based aid is available through our financial aid office. "
            "Applications for scholarships are due by June 1 for the fall intake."
        ),
        "category": "financial-aid",
    },
    {
        "question": "What campus facilities are available?",
        "answer": (
            "Our campus features a digital library, science laboratories, "
            "a 500-seat auditorium, sports complex, and on-campus student housing. "
            "The innovation hub is open 24 hours for enrolled students."
        ),
        "category": "facilities",
    },
    {
        "question": "Are online classes available?",
        "answer": (
            "Yes. All core programs offer hybrid or fully online options. "
            "Live lectures are streamed in real time and recorded for later review."
        ),
        "category": "programs",
    },
    {
        "question": "How do I transfer credits from another institution?",
        "answer": (
            "Submit official transcripts to the admissions office. "
            "Transfer credits are evaluated within 10 business days. "
            "Up to 60 credits may be transferred toward a bachelor's degree."
        ),
        "category": "admissions",
    },
    {
        "question": "What is the student-to-faculty ratio?",
        "answer": (
            "Our average student-to-faculty ratio is 12 to 1. "
            "Small class sizes ensure personalised attention and mentorship."
        ),
        "category": "academics",
    },
    {
        "question": "Is career counselling provided?",
        "answer": (
            "Yes. The career centre offers resume reviews, mock interviews, "
            "and employer networking events. Placement support continues for one year after graduation."
        ),
        "category": "student-services",
    },
    {
        "question": "What are the English language requirements?",
        "answer": (
            "International applicants must submit IELTS 6.5, TOEFL 80, or equivalent. "
            "Conditional admission is available with an intensive English pathway program."
        ),
        "category": "admissions",
    },
]


# ---------------------------------------------------------------------------
# Sample course catalogue
# ---------------------------------------------------------------------------

EDUCATION_COURSES: List[CourseRecord] = [
    CourseRecord(
        name="Computer Science Bachelor",
        category="technology",
        duration_months=48,
        tuition_usd=48000.0,
        description="Full-stack software engineering, algorithms, and systems design.",
        prerequisites=["High school mathematics", "Introductory programming"],
    ),
    CourseRecord(
        name="Data Science Master",
        category="technology",
        duration_months=24,
        tuition_usd=32000.0,
        description="Machine learning, statistical modelling, and big-data pipelines.",
        prerequisites=["Linear algebra", "Probability and statistics"],
    ),
    CourseRecord(
        name="Business Administration MBA",
        category="business",
        duration_months=24,
        tuition_usd=45000.0,
        description="Leadership, strategy, finance, and entrepreneurship.",
        prerequisites=["Bachelor's degree", "Two years work experience"],
    ),
    CourseRecord(
        name="Digital Marketing Certificate",
        category="business",
        duration_months=6,
        tuition_usd=4500.0,
        description="SEO, SEM, social media strategy, and content marketing.",
        prerequisites=["None"],
    ),
    CourseRecord(
        name="Graphic Design Diploma",
        category="arts",
        duration_months=18,
        tuition_usd=18000.0,
        description="Visual communication, typography, and UX fundamentals.",
        prerequisites=["Creative portfolio"],
    ),
    CourseRecord(
        name="Nursing Bachelor",
        category="healthcare",
        duration_months=48,
        tuition_usd=52000.0,
        description="Clinical practice, patient care, and healthcare systems.",
        prerequisites=["Biology and chemistry", "CPR certification"],
    ),
]


# ---------------------------------------------------------------------------
# Sample admissions records
# ---------------------------------------------------------------------------

EDUCATION_ADMISSIONS: List[AdmissionRecord] = [
    AdmissionRecord(
        student_id="EDU-2026-001",
        name="Alice Johnson",
        program="Computer Science Bachelor",
        status="accepted",
        submitted_date="2026-02-10",
        decision_date="2026-03-15",
        notes="Merit scholarship approved.",
    ),
    AdmissionRecord(
        student_id="EDU-2026-002",
        name="Bob Smith",
        program="Data Science Master",
        status="pending",
        submitted_date="2026-04-01",
        decision_date="",
        notes="Awaiting transcript evaluation.",
    ),
    AdmissionRecord(
        student_id="EDU-2026-003",
        name="Carol White",
        program="Business Administration MBA",
        status="waitlisted",
        submitted_date="2026-01-20",
        decision_date="2026-03-01",
        notes="Position 5 on waitlist.",
    ),
    AdmissionRecord(
        student_id="EDU-2026-004",
        name="David Lee",
        program="Nursing Bachelor",
        status="rejected",
        submitted_date="2026-03-05",
        decision_date="2026-04-10",
        notes="Prerequisites incomplete.",
    ),
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed_education_db() -> Dict[str, Any]:
    """
    Initialise and return the in-memory education database.

    Returns a dictionary containing course catalogue, admissions records,
    FAQ entries, and campus-visit booking ledger. This structure is
    consumed by the education-domain tools at receptionist start-up.

    Returns:
        A dict with keys: ``courses``, ``admissions``, ``faqs``, ``bookings``.
    """
    return {
        "courses": list(EDUCATION_COURSES),
        "admissions": list(EDUCATION_ADMISSIONS),
        "faqs": list(EDUCATION_FAQ),
        "bookings": [],  # List of scheduled campus visits
    }


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
