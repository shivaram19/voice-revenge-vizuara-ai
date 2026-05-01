"""
Jaya High School, Suryapet — School Configuration
==================================================
Static identity used for greetings, business-hour lookups, and any
LLM-context block that names the school. Sourced from the school's
public registration record (icbse.com Jaya HS Suryapeta listing,
verified 2026-04-30) and DFS-007 §2.2.

Ref: DFS-007 §2.2 (school particulars); ADR-009 (domain modularity).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SchoolConfig:
    """Static identity of a tenant school."""

    school_name: str
    address: str
    state: str
    district: str
    pincode: str
    medium: str
    affiliation: str            # "State Board" | "CBSE" | "ICSE"
    grades: str                 # "Class 1 - 10"
    business_hours: str
    phone: str
    email: str
    primary_language: str       # the dominant local language
    secondary_language: str     # next-most-common
    closing_blessing: str       # culturally-natural farewell line
    # Sarvam AI voice config — used when primary_language is an Indian language
    sarvam_language_code: str = "te-IN"   # BCP-47 for Sarvam STT/TTS
    sarvam_speaker: str = "kavya"         # Bulbul v3 speaker (female, Telugu)
    sarvam_speaker_male: str = "rohan"    # Bulbul v3 male fallback


JAYA_SCHOOL_CONFIG = SchoolConfig(
    school_name="Jaya High School, Suryapet",
    address="Sixty Feet Road, Suryapet",
    state="Telangana",
    district="Suryapet (formerly Nalgonda)",
    pincode="508213",
    medium="English (Telugu spoken)",
    affiliation="State Board",
    grades="Class 1 to Class 10",
    business_hours="Monday through Saturday, 8:30 AM to 4 PM. Sunday holiday.",
    phone="+91-9491-116-789",  # placeholder — update with school's official line
    email="office@jayahighschool.in",  # placeholder
    primary_language="Telugu",
    secondary_language="English",
    closing_blessing="Have a peaceful day, sir.",
)


# References
# - DFS-007 §2.2: School particulars confirmed via icbse.com listing.
# - ADR-009: Domain-modular voice agent platform.
