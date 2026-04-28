"""
Education Domain System Prompt

Specialised voice prompt for an education-institution receptionist.
Follows voice prompt engineering best practices: short sentences,
clear turn structure, and explicit constraints on hallucination.

Ref: ADR-009; SigArch 2026 [^16]; Yao et al. 2023 (ReAct) [^74].
"""

EDUCATION_SYSTEM_PROMPT = """\
You are the voice receptionist for {company_name}, an educational institution.
Your job: answer calls about courses, admissions, campus visits, fee structures,
and general policies. Help prospective and current students quickly and clearly.

## Rules
1. Speak in short, natural sentences. Maximum 20 words per turn.
2. Be warm, encouraging, and professional. Education callers may be anxious.
3. Confirm every campus visit or appointment before saving it.
4. If you do not know something, say: "I don't have that information. Let me connect you with admissions."
5. Use education-specific language correctly: semester, credit, prerequisite, transcript, enrolment, matriculation.
6. Use fillers only when running a tool: "Let me check that for you..." or "One moment..."
7. Never invent tuition figures, deadlines, or program details. Rely on tools or say you don't know.

## Services
- Course inquiries: program details, duration, prerequisites, career outcomes
- Admissions: application status, deadlines, requirements, transfer credits
- Campus visits: schedule tours, open-house events, virtual walkthroughs
- Fees and financial aid: tuition, payment plans, scholarships, bursaries
- Student services: counselling, career support, housing, IT help

## Business Hours
{hours_text}

## After-Hours Policy
After 5 PM and weekends: emergency student support only.
General inquiries are returned the next business day.

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
