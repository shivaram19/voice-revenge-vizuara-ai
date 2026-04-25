"""
Construction Receptionist Demo
Simulated call scenarios for a building trades company.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.receptionist.models import Database
from src.receptionist.construction_seed import seed_database, CONSTRUCTION_FAQ
from src.receptionist.tools.faq import FAQKnowledgeBase, FAQChunk
from src.receptionist.tools.contractor_tools import ContractorDirectory, OutboundCallManager
from src.receptionist.scheduler import SchedulingEngine
from src.receptionist.outbound_caller import OutboundCaller


def demo():
    print("=" * 60)
    print("CONSTRUCTION RECEPTIONIST DEMO")
    print("BuildPro Contracting — Essex County, NJ")
    print("=" * 60)

    # Fresh database with construction data
    db = Database(":memory:")
    seed_database(db)

    # Load FAQ
    faq = FAQKnowledgeBase()
    for item in CONSTRUCTION_FAQ:
        faq.add(FAQChunk(text=item["text"], source="company_handbook", category=item["category"]))

    # Tools
    contractors = ContractorDirectory(db)
    scheduler = SchedulingEngine(db)
    caller = OutboundCaller(db)

    print("\n--- SCENARIO 1: Emergency Plumbing Call ---")
    results = contractors.find_contractors("plumbing")
    print(f"Found: {contractors.format_for_voice(results)}")

    # Check availability for today
    from datetime import date
    slots = scheduler.get_available_slots(results[0].id, date.today())
    print(f"Today's slots: {scheduler.format_slots_for_voice(slots[:3])}")

    print("\n--- SCENARIO 2: Kitchen Renovation Estimate ---")
    gc_results = contractors.find_contractors("general")
    print(f"Found: {contractors.format_for_voice(gc_results)}")

    print("\n--- SCENARIO 3: FAQ — Emergency Rates ---")
    answer = faq.format_for_voice(faq.search("emergency after hours"))
    print(f"FAQ: {answer}")

    print("\n--- SCENARIO 4: FAQ — Permits ---")
    answer = faq.format_for_voice(faq.search("permits"))
    print(f"FAQ: {answer}")

    print("\n--- SCENARIO 5: Schedule Outbound Call to Electrician ---")
    elec_results = contractors.find_contractors("electrical")
    if elec_results:
        manager = OutboundCallManager(db)
        success, msg, task_id = manager.schedule_call_to_contractor(
            elec_results[0].id,
            "Confirm panel upgrade materials delivery for tomorrow",
        )
        print(f"Outbound: {msg}")

    print("\n--- SCENARIO 6: Book Appointment ---")
    if gc_results:
        from datetime import datetime, time
        tomorrow = date.today() + __import__('datetime').timedelta(days=1)
        appt_time = datetime.combine(tomorrow, time(10, 0))
        result = contractors.book_appointment(
            contractor_id=gc_results[0].id,
            caller_name="Jane Doe",
            caller_phone="5558888",
            start_time=appt_time,
            duration_minutes=60,
            appointment_type=__import__('src.receptionist.models', fromlist=['AppointmentType']).AppointmentType.IN_PERSON,
            notes="Kitchen renovation estimate",
        )
        print(f"Booking: {result.message}")

    print("\n" + "=" * 60)
    print("All scenarios completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
