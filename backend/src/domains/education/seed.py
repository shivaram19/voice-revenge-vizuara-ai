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
        "question": "What is the ANN Explorer course?",
        "answer": (
            "ANN Explorer is our 12-week Artificial Neural Networks program for students in Grade 6 and above. "
            "Children learn how computers recognise images, understand speech, and make decisions — just like a human brain. "
            "They build real projects: an emoji recogniser, a simple chatbot, and a music genre classifier. "
            "No advanced mathematics is required. We use visual coding tools that make AI concepts easy and fun."
        ),
        "category": "courses",
    },
    {
        "question": "What is the fee for the ANN course, and are there instalments?",
        "answer": (
            "The full ANN Explorer program fee is 24,000 rupees for 12 weeks. "
            "We offer a 3-month EMI option at no extra cost. "
            "A sibling discount of 10 percent is available for families enrolling more than one child."
        ),
        "category": "fees",
    },
    {
        "question": "When does the next ANN batch start?",
        "answer": (
            "The next ANN Explorer batch begins on June 2nd, 2026. "
            "Classes are held on Saturdays and Sundays from 10 AM to 12 noon. "
            "Each batch has only 12 students to ensure individual attention. "
            "Four seats are still available for the June batch."
        ),
        "category": "courses",
    },
    {
        "question": "Does my child need to know coding before joining ANN?",
        "answer": (
            "No prior coding experience is needed. The course starts with drag-and-drop visual tools. "
            "By the middle of the program, students transition to simple Python, guided step by step. "
            "Basic computer literacy — using a mouse and keyboard — is sufficient."
        ),
        "category": "courses",
    },
    {
        "question": "What other courses do you offer?",
        "answer": (
            "We offer Python Programming, Robotics and IoT, Mathematics Excellence, Science Lab Mastery, "
            "and Spoken English. All programs are designed for school students from Grade 5 to Grade 10."
        ),
        "category": "courses",
    },
    {
        "question": "How can I visit the school before enrolling?",
        "answer": (
            "You are welcome to visit Jaya High School any weekday between 9 AM and 4 PM. "
            "We also schedule dedicated campus tours on Saturday mornings. "
            "Please call ahead so we can arrange a faculty member to meet you."
        ),
        "category": "facilities",
    },
    {
        "question": "Is there a demo class before I pay?",
        "answer": (
            "Yes. We hold a free demo class every Saturday at 11 AM. "
            "Your child can experience the ANN Explorer session firsthand. "
            "After the demo, you can decide whether to enrol. There is no obligation."
        ),
        "category": "admissions",
    },
    {
        "question": "What certificate will my child receive?",
        "answer": (
            "Upon completion, every student receives a certificate of achievement from Jaya High School. "
            "Outstanding projects are also featured in our annual science exhibition."
        ),
        "category": "courses",
    },
]


# ---------------------------------------------------------------------------
# Sample course catalogue
# ---------------------------------------------------------------------------

EDUCATION_COURSES: List[CourseRecord] = [
    CourseRecord(
        name="ANN Explorer — Artificial Neural Networks",
        category="technology",
        duration_months=3,
        tuition_usd=288.0,  # ₹24,000 ≈ $288
        description=(
            "12-week after-school program for Grade 6 and above. "
            "Students build emoji recognisers, simple chatbots, and music classifiers "
            "using visual neural network tools. No advanced math required. "
            "Batch size: 12 students. Includes take-home project kit and certificate."
        ),
        prerequisites=["Grade 6 or above", "Basic computer literacy"],
    ),
    CourseRecord(
        name="Python Programming Fundamentals",
        category="technology",
        duration_months=3,
        tuition_usd=180.0,  # ₹15,000 ≈ $180
        description="Introduction to Python coding, logic building, and small projects.",
        prerequisites=["Grade 5 or above"],
    ),
    CourseRecord(
        name="Robotics and IoT Workshop",
        category="technology",
        duration_months=2,
        tuition_usd=144.0,  # ₹12,000 ≈ $144
        description="Hands-on robotics with Arduino, sensors, and basic automation.",
        prerequisites=["Grade 7 or above"],
    ),
    CourseRecord(
        name="Mathematics Excellence Program",
        category="academics",
        duration_months=6,
        tuition_usd=120.0,  # ₹10,000 ≈ $120
        description="Advanced problem solving, Olympiad preparation, and board exam readiness.",
        prerequisites=["Grade 6 or above"],
    ),
    CourseRecord(
        name="Science Lab Mastery",
        category="academics",
        duration_months=4,
        tuition_usd=96.0,  # ₹8,000 ≈ $96
        description="Practical physics, chemistry, and biology experiments with lab access.",
        prerequisites=["Grade 8 or above"],
    ),
    CourseRecord(
        name="Spoken English and Communication",
        category="arts",
        duration_months=3,
        tuition_usd=72.0,  # ₹6,000 ≈ $72
        description="Public speaking, debate, interview skills, and confident communication.",
        prerequisites=["Grade 5 or above"],
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
