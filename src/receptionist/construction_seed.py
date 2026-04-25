"""
Construction Industry Seed Data
Populates the receptionist database with realistic contractors,
services, and FAQ for a construction/building trades company.
"""

from datetime import datetime, date, time, timedelta
from src.receptionist.models import Database, Contractor, Appointment, AppointmentStatus, AppointmentType
from src.receptionist.scheduler import SchedulingEngine


def seed_database(db: Database) -> None:
    """
    Seed the database with construction contractors and sample data.
    Call this on first startup.
    """
    contractors = [
        Contractor(id=None, name="Mike Ross", phone="5550101", email="mike.ross@buildpro.com",
                   specialty="General Contracting", timezone="America/New_York", daily_limit=6),
        Contractor(id=None, name="Sarah Chen", phone="5550102", email="sarah.chen@buildpro.com",
                   specialty="Electrical", timezone="America/New_York", daily_limit=8),
        Contractor(id=None, name="James O'Brien", phone="5550103", email="james.obrien@buildpro.com",
                   specialty="Plumbing", timezone="America/New_York", daily_limit=8),
        Contractor(id=None, name="Elena Vasquez", phone="5550104", email="elena.vasquez@buildpro.com",
                   specialty="HVAC", timezone="America/New_York", daily_limit=6),
        Contractor(id=None, name="David Kim", phone="5550105", email="david.kim@buildpro.com",
                   specialty="Roofing", timezone="America/New_York", daily_limit=5),
        Contractor(id=None, name="Aisha Johnson", phone="5550106", email="aisha.johnson@buildpro.com",
                   specialty="Framing & Carpentry", timezone="America/New_York", daily_limit=6),
        Contractor(id=None, name="Tom Bradley", phone="5550107", email="tom.bradley@buildpro.com",
                   specialty="Concrete & Masonry", timezone="America/New_York", daily_limit=5),
        Contractor(id=None, name="Lisa Park", phone="5550108", email="lisa.park@buildpro.com",
                   specialty="Drywall & Painting", timezone="America/New_York", daily_limit=8),
        Contractor(id=None, name="Carlos Mendez", phone="5550109", email="carlos.mendez@buildpro.com",
                   specialty="Flooring & Tile", timezone="America/New_York", daily_limit=6),
        Contractor(id=None, name="Rachel Green", phone="5550110", email="rachel.green@buildpro.com",
                   specialty="Permits & Inspections", timezone="America/New_York", daily_limit=4),
    ]

    contractor_ids = {}
    for c in contractors:
        cid = db.add_contractor(c)
        contractor_ids[c.specialty] = cid
        print(f"  Added contractor: {c.name} ({c.specialty})")

    # Pre-seed some appointments for demo realism
    scheduler = SchedulingEngine(db)
    today = date.today()

    # Mike Ross has a site walkthrough at 10 AM
    scheduler.book_appointment(
        contractor_ids["General Contracting"],
        "Homeowner", "5559991",
        datetime.combine(today, time(10, 0)),
        duration_minutes=60,
        appointment_type=AppointmentType.IN_PERSON,
        notes="Kitchen renovation site survey",
    )

    # Sarah Chen has an electrical inspection at 2 PM
    scheduler.book_appointment(
        contractor_ids["Electrical"],
        "Builder Corp", "5559992",
        datetime.combine(today, time(14, 0)),
        duration_minutes=45,
        appointment_type=AppointmentType.IN_PERSON,
        notes="Panel upgrade inspection",
    )

    # James O'Brien has a plumbing emergency call at 9 AM
    scheduler.book_appointment(
        contractor_ids["Plumbing"],
        "Property Mgmt", "5559993",
        datetime.combine(today, time(9, 0)),
        duration_minutes=30,
        appointment_type=AppointmentType.PHONE,
        notes="Burst pipe emergency consultation",
    )

    print(f"\nSeeded {len(contractors)} contractors and 3 sample appointments.")


CONSTRUCTION_FAQ = [
    {
        "text": "We offer 24/7 emergency repair services for plumbing, electrical, and HVAC. After-hours rates apply from 6 PM to 8 AM weekdays and all weekend.",
        "category": "emergency",
    },
    {
        "text": "Free estimates are provided for all projects over $1,000. Estimates take 30 to 60 minutes and are scheduled within 48 hours of your call.",
        "category": "estimates",
    },
    {
        "text": "We are fully licensed and insured. Our license number is GC-2024-8847. Certificates of insurance are available upon request.",
        "category": "licensing",
    },
    {
        "text": "Project timelines vary by scope. A bathroom remodel typically takes 2 to 3 weeks. A full kitchen renovation takes 4 to 6 weeks. Additions take 8 to 12 weeks.",
        "category": "timelines",
    },
    {
        "text": "We handle permit applications for all projects requiring town approval. Permit fees are itemized in your quote. Inspection scheduling is included.",
        "category": "permits",
    },
    {
        "text": "Our workmanship warranty is 1 year on all labor. Manufacturer warranties apply to materials and vary by product, typically 5 to 25 years.",
        "category": "warranty",
    },
    {
        "text": "Payment terms are 30 percent deposit, 40 percent at rough-in, and 30 percent upon final inspection and sign-off. We accept check, ACH, and credit card.",
        "category": "payment",
    },
    {
        "text": "Our service area covers all of Essex, Middlesex, and Suffolk counties. Travel fees apply for projects beyond 30 miles from our office.",
        "category": "service_area",
    },
]


if __name__ == "__main__":
    db = Database("construction_receptionist.db")
    seed_database(db)
