"""
Pharma domain seed data and database initializer.

Provides sample drug records, prescription records, FAQ entries, and an
adverse-event log for demonstration and integration testing. All data is
in-memory; production deployments swap this for a real pharmacy information
system (e.g., RxNorm, Surescripts).

Ref: SigArch 2026 [^16]; OpenAI Function Calling API [^13].
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class DrugRecord:
    """A single drug entry in the pharmacy formulary."""
    name: str
    generic_name: str
    dosage: str
    side_effects: List[str]
    warnings: List[str]
    category: str
    storage: str


@dataclass
class PrescriptionRecord:
    """A single prescription fill record."""
    prescription_id: str
    patient_name: str
    drug_name: str
    status: str  # e.g., "ready", "pending", "in_process", "delayed"
    refills_remaining: int
    total_refills: int
    prescribed_date: str
    last_filled_date: str
    notes: str


@dataclass
class AdverseEventRecord:
    """A single adverse drug reaction report."""
    report_id: str
    drug_name: str
    symptoms: List[str]
    severity: str  # mild, moderate, severe
    reported_at: str
    status: str = "logged"


# ---------------------------------------------------------------------------
# Sample FAQ entries
# ---------------------------------------------------------------------------

PHARMA_FAQ: List[Dict[str, str]] = [
    {
        "question": "Do you accept insurance?",
        "answer": (
            "Yes, we accept most major insurance plans including Medicare and Medicaid. "
            "Please bring your insurance card and a valid photo ID to every visit."
        ),
        "category": "insurance",
    },
    {
        "question": "Can I get generic versions of my medication?",
        "answer": (
            "In most cases, yes. Generic equivalents contain the same active ingredients "
            "and are approved by the FDA. Ask your pharmacist if a generic is available for your prescription."
        ),
        "category": "generics",
    },
    {
        "question": "How should I store my medication?",
        "answer": (
            "Most medications should be stored in a cool, dry place away from direct sunlight. "
            "Some medications require refrigeration. Check the label or ask your pharmacist for specific instructions."
        ),
        "category": "storage",
    },
    {
        "question": "What are your pharmacy hours?",
        "answer": (
            "Prescription pickup is available 24 hours. Pharmacy consultation and prescription filling "
            "are available from 8 AM to 8 PM, seven days a week."
        ),
        "category": "hours",
    },
    {
        "question": "How do I transfer a prescription from another pharmacy?",
        "answer": (
            "Provide us with your previous pharmacy's name and phone number, along with the prescription details. "
            "We will contact them on your behalf to transfer the remaining refills."
        ),
        "category": "transfers",
    },
    {
        "question": "What should I do if I miss a dose?",
        "answer": (
            "Take the missed dose as soon as you remember, unless it is almost time for your next dose. "
            "Do not double up. When in doubt, call your pharmacist or prescriber for guidance."
        ),
        "category": "medication-use",
    },
    {
        "question": "Do you offer medication delivery?",
        "answer": (
            "Yes, we offer same-day delivery within a 10-mile radius and next-day delivery for addresses outside that range. "
            "Delivery is free for prescriptions over 35 dollars."
        ),
        "category": "delivery",
    },
    {
        "question": "Can I set up automatic prescription refills?",
        "answer": (
            "Yes. Enrol in our auto-refill program and we will process your refill when it is due. "
            "You will receive a text or call when it is ready for pickup or delivery."
        ),
        "category": "refills",
    },
]


# ---------------------------------------------------------------------------
# Sample drug catalogue
# ---------------------------------------------------------------------------

PHARMA_DRUGS: List[DrugRecord] = [
    DrugRecord(
        name="Aspirin",
        generic_name="Acetylsalicylic Acid",
        dosage="81 mg to 325 mg once daily, or as directed by your physician.",
        side_effects=["stomach upset", "heartburn", "mild headache", "nausea"],
        warnings=[
            "Do not use in children or teenagers with viral infections.",
            "May increase bleeding risk. Consult your doctor before surgery.",
        ],
        category="Analgesic / Antiplatelet",
        storage="Room temperature, away from moisture.",
    ),
    DrugRecord(
        name="Metformin",
        generic_name="Metformin Hydrochloride",
        dosage="500 mg to 1000 mg twice daily with meals, or as prescribed.",
        side_effects=["diarrhoea", "nausea", "abdominal discomfort", "metallic taste"],
        warnings=[
            "Rare risk of lactic acidosis. Seek immediate medical attention for muscle pain or breathing difficulty.",
            "Avoid excessive alcohol while taking this medication.",
        ],
        category="Antidiabetic",
        storage="Room temperature, tightly closed container.",
    ),
    DrugRecord(
        name="Lisinopril",
        generic_name="Lisinopril",
        dosage="5 mg to 40 mg once daily, as directed by your physician.",
        side_effects=["dry cough", "dizziness", "headache", "fatigue"],
        warnings=[
            "Do not use during pregnancy. May cause injury or death to the developing fetus.",
            "Monitor blood pressure regularly.",
        ],
        category="ACE Inhibitor",
        storage="Room temperature, protect from light and moisture.",
    ),
    DrugRecord(
        name="Atorvastatin",
        generic_name="Atorvastatin Calcium",
        dosage="10 mg to 80 mg once daily, typically in the evening.",
        side_effects=["muscle pain", "joint pain", "diarrhoea", "mild nausea"],
        warnings=[
            "Report unexplained muscle pain or weakness immediately.",
            "Avoid grapefruit and grapefruit juice while taking this medication.",
        ],
        category="Statin",
        storage="Room temperature, away from moisture and heat.",
    ),
    DrugRecord(
        name="Amoxicillin",
        generic_name="Amoxicillin",
        dosage="250 mg to 500 mg every 8 hours, or 875 mg every 12 hours, as prescribed.",
        side_effects=["rash", "diarrhoea", "nausea", "vomiting"],
        warnings=[
            "Do not use if allergic to penicillin. Seek emergency care for severe allergic reactions.",
            "Complete the full course even if symptoms improve.",
        ],
        category="Antibiotic",
        storage="Room temperature. Oral suspension may require refrigeration after reconstitution.",
    ),
    DrugRecord(
        name="Ibuprofen",
        generic_name="Ibuprofen",
        dosage="200 mg to 400 mg every 4 to 6 hours as needed. Do not exceed 1200 mg per day without medical supervision.",
        side_effects=["stomach pain", "heartburn", "dizziness", "mild headache"],
        warnings=[
            "May increase risk of heart attack or stroke with prolonged use.",
            "Avoid if you have a history of stomach ulcers or kidney disease unless directed by a physician.",
        ],
        category="NSAID",
        storage="Room temperature, away from moisture and heat.",
    ),
]


# ---------------------------------------------------------------------------
# Sample prescription records
# ---------------------------------------------------------------------------

PHARMA_PRESCRIPTIONS: List[PrescriptionRecord] = [
    PrescriptionRecord(
        prescription_id="RX-2026-1001",
        patient_name="Alice Johnson",
        drug_name="Metformin",
        status="ready",
        refills_remaining=2,
        total_refills=3,
        prescribed_date="2026-04-01",
        last_filled_date="2026-04-15",
        notes="Ready for pickup at the main counter.",
    ),
    PrescriptionRecord(
        prescription_id="RX-2026-1002",
        patient_name="Bob Smith",
        drug_name="Lisinopril",
        status="in_process",
        refills_remaining=1,
        total_refills=5,
        prescribed_date="2026-03-20",
        last_filled_date="2026-04-10",
        notes="Insurance verification in progress. Estimated ready by 6 PM.",
    ),
    PrescriptionRecord(
        prescription_id="RX-2026-1003",
        patient_name="Carol White",
        drug_name="Amoxicillin",
        status="ready",
        refills_remaining=0,
        total_refills=0,
        prescribed_date="2026-04-20",
        last_filled_date="2026-04-20",
        notes="No refills remaining. Contact prescriber for a new prescription.",
    ),
    PrescriptionRecord(
        prescription_id="RX-2026-1004",
        patient_name="David Lee",
        drug_name="Atorvastatin",
        status="delayed",
        refills_remaining=3,
        total_refills=6,
        prescribed_date="2026-04-05",
        last_filled_date="2026-03-05",
        notes="Manufacturer backorder. Expected restock by April 25.",
    ),
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed_pharma_db() -> Dict[str, Any]:
    """
    Initialise and return the in-memory pharmacy database.

    Returns a dictionary containing drug formulary, prescription records,
    FAQ entries, and adverse-event log. This structure is consumed by the
    pharma-domain tools at receptionist start-up.

    Returns:
        A dict with keys: ``drugs``, ``prescriptions``, ``faqs``, ``adverse_events``.
    """
    return {
        "drugs": list(PHARMA_DRUGS),
        "prescriptions": list(PHARMA_PRESCRIPTIONS),
        "faqs": list(PHARMA_FAQ),
        "adverse_events": [],  # List of logged AdverseEventRecord instances
    }


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
