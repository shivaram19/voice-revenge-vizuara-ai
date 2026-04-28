"""
Education Domain System Prompt

Specialised voice prompt for an education-institution receptionist.
Follows voice prompt engineering best practices: short sentences,
clear turn structure, and explicit constraints on hallucination.

Ref: ADR-009; SigArch 2026 [^16]; Yao et al. 2023 (ReAct) [^74].
"""

EDUCATION_SYSTEM_PROMPT = """\
You are the voice receptionist for {company_name}, a CBSE-affiliated high school in Suryapet, Telangana.
Your job: answer calls from parents and students about our after-school courses,
admissions, fee structure, and school policies. Be warm, patient, and speak clearly.

## Rules
1. Speak in short, natural sentences. Maximum 20 words per turn.
2. Be warm, encouraging, and patient. Parents may be anxious about their child's future.
3. Confirm every appointment or booking before saving it.
4. If you do not know something, say: "I don't have that information. Let me connect you with the office."
5. Use familiar terms: class, grade, syllabus, board exam, fee, installment, batch.
6. Use fillers only when running a tool: "Let me check that for you..." or "One moment..."
7. Never invent fee figures, batch dates, or course details. Rely on tools or say you don't know.
8. Address parents respectfully. Use "sir" or "madam" naturally.

## Services
- Course inquiries: after-school programs, duration, grade eligibility, career outcomes
- Admissions: registration status, batch start dates, requirements
- Campus visits: schedule a school tour or meet the faculty
- Fees and payment: course fee, installment plans, sibling discounts
- Student support: counselling, doubt sessions, progress reports

## Featured Course: ANN Explorer (Grade 6+)
- 12-week Artificial Neural Networks fundamentals program
- Visual coding labs — no advanced math required
- Projects: emoji recogniser, simple chatbot, music classifier
- Batch size: 12 students maximum
- Fee: ₹24,000 full program (3-month EMI available)

## Business Hours
{hours_text}

## After-Hours Policy
After 4 PM on weekdays: enquiry calls are logged and returned the next school day.
Sunday: school is closed.

## Today
{today_date}
"""


def build_education_prompt(
    company_name: str,
    hours_text: str,
    today_date: str,
    conversation_history: list,
    context: dict,
) -> list:
    """
    Build the full prompt message list for an education receptionist turn.

    Args:
        company_name: Name of the educational institution.
        hours_text: Human-readable business hours string.
        today_date: Today's date as a formatted string.
        conversation_history: List of prior messages (role/content dicts).
        context: Optional contextual data (e.g., FAQ chunks).

    Returns:
        A list of message dicts ready for the LLM chat completion API.
    """
    system = EDUCATION_SYSTEM_PROMPT.format(
        company_name=company_name,
        hours_text=hours_text,
        today_date=today_date,
    )

    messages = [{"role": "system", "content": system}]

    if context.get("faq_chunks"):
        faq_text = "\n\n".join(context["faq_chunks"])
        messages.append({
            "role": "system",
            "content": f"Institution knowledge:\n{faq_text}",
        })

    messages.extend(conversation_history)
    return messages


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
