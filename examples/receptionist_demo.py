"""
AI Receptionist Demo
Runs a simulated call through the full receptionist pipeline.
No telephony or LLM required — uses mock LLM responses for demonstration.

Ref: ADR-005; SigArch 2026 streaming architecture; Yao et al. 2023 ReAct.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import datetime, timedelta

from src.receptionist.service import ReceptionistService, ReceptionistConfig, CallSession
from src.receptionist.tools.contact_lookup import ContactDirectory, Contact
from src.receptionist.tools.calendar import Calendar
from src.receptionist.tools.faq import FAQKnowledgeBase, FAQChunk
from src.receptionist.tools.messages import MessageLog


class MockLLMClient:
    """
    Mock LLM that simulates tool-calling behavior for demonstration.
    Production: replace with OpenAI/Anthropic/vLLM client.
    Ref: OpenAI. (2023). Function Calling API.
    """

    def __init__(self, contacts: ContactDirectory, calendar: Calendar, faq: FAQKnowledgeBase):
        self.contacts = contacts
        self.calendar = calendar
        self.faq = faq

    async def chat_completion(self, messages, tools):
        # Get the last user message
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break

        user_lower = last_user.lower()

        # Simple intent routing
        if "speak to" in user_lower or "reach" in user_lower or "find" in user_lower:
            return {
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "function": {
                        "name": "lookup_contact",
                        "arguments": f'{{"query": "{last_user}"}}',
                    },
                }],
            }

        if "book" in user_lower or "appointment" in user_lower or "schedule" in user_lower:
            return {
                "content": None,
                "tool_calls": [{
                    "id": "call_2",
                    "function": {
                        "name": "check_calendar",
                        "arguments": '{"action": "check", "service": "Consultation", "date": "' + datetime.utcnow().strftime("%Y-%m-%d") + '"}',
                    },
                }],
            }

        if "hours" in user_lower or "location" in user_lower or "address" in user_lower:
            return {
                "content": None,
                "tool_calls": [{
                    "id": "call_3",
                    "function": {
                        "name": "search_faq",
                        "arguments": f'{{"query": "{last_user}"}}',
                    },
                }],
            }

        if "message" in user_lower or "voicemail" in user_lower:
            return {
                "content": None,
                "tool_calls": [{
                    "id": "call_4",
                    "function": {
                        "name": "take_message",
                        "arguments": '{"recipient": "Dr. Chen", "content": "Call me back about the lab results.", "caller_name": "John Doe"}',
                    },
                }],
            }

        # Direct response
        return {
            "content": "I'm here to help. Would you like to book an appointment, speak with someone, or leave a message?"
        }


async def main():
    print("=" * 60)
    print("AI RECEPTIONIST DEMO")
    print("=" * 60)

    # Setup data
    contacts = ContactDirectory()
    contacts.add(Contact("Dr. Sarah Chen", "Cardiologist", "Medical", "101", "s.chen@acme.com"))
    contacts.add(Contact("James Wilson", "Sales Manager", "Sales", "202", "j.wilson@acme.com"))
    contacts.add(Contact("Lisa Park", "Support Lead", "Support", "303", "l.park@acme.com"))

    calendar = Calendar()
    calendar.add_service("Consultation")
    # Pre-book one slot so there's realistic availability
    calendar.book(
        service="Consultation",
        start=datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0),
        duration_minutes=30,
        booked_by="Existing Patient",
    )

    faq = FAQKnowledgeBase()
    faq.add(FAQChunk(
        text="Our business hours are Monday through Friday, 9 AM to 5 PM. We are closed weekends.",
        source="company_handbook",
        category="hours",
    ))
    faq.add(FAQChunk(
        text="We are located at 123 Main Street, Suite 400, Downtown.",
        source="company_handbook",
        category="location",
    ))

    messages = MessageLog()

    # Mock LLM
    llm = MockLLMClient(contacts, calendar, faq)

    # Build service
    config = ReceptionistConfig(
        company_name="Acme Medical",
        hours_text="Monday through Friday, 9 AM to 5 PM.",
    )

    service = ReceptionistService(
        config=config,
        contacts=contacts,
        calendar=calendar,
        faq=faq,
        messages=messages,
        llm_client=llm,
        tts_service=None,  # Demo: text-only
    )

    # Bind mock LLM method
    service._llm_chat_completion = llm.chat_completion

    # Simulate call
    session_id = "demo-call-001"
    caller = "+1-555-0199"
    called = "+1-555-0100"

    greeting = await service.handle_call_start(session_id, caller, called)
    print(f"\n[AGENT] {greeting}")

    # Simulate conversation turns
    turns = [
        "I'd like to speak with Dr. Chen.",
        "What are your business hours?",
        "Can I book a consultation for today?",
        "I'd like to leave a message for Dr. Chen.",
    ]

    for turn in turns:
        print(f"\n[CALLER] {turn}")
        response = await service.handle_transcript(session_id, turn)
        print(f"[AGENT] {response}")

    # End call
    session = await service.handle_call_end(session_id)
    print(f"\n{'=' * 60}")
    print("CALL SUMMARY")
    print(f"{'=' * 60}")
    print(f"Session ID: {session.session_id}")
    print(f"Duration: {datetime.utcnow() - session.start_time}")
    print(f"Contact lookup: {session.contact_result}")
    print(f"Booking: {session.booking_result}")
    print(f"Message: {session.message_result}")
    print(f"Total turns: {len(session.conversation_history)}")


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.

if __name__ == "__main__":
    asyncio.run(main())
