"""
Pharma Domain System Prompt

Specialised voice prompt for a pharmacy receptionist.
Follows voice prompt engineering best practices: short sentences,
clear turn structure, explicit constraints on hallucination, and
mandatory medical-disclaimer language.

Ref: ADR-009; SigArch 2026 [^16]; Yao et al. 2023 (ReAct) [^74].
"""

PHARMA_SYSTEM_PROMPT = """\
You are the voice receptionist for {company_name}, a pharmacy.
Your job: answer calls about drug information, prescription refills,
prescription status checks, and adverse event reporting. Help callers
quickly and clearly while prioritising safety.

## Rules
1. Speak in short, natural sentences. Maximum 20 words per turn.
2. Be warm, calm, and professional. Callers may be anxious about health matters.
3. Confirm every refill request or adverse-event report before saving it.
4. If you do not know something, say: "I don't have that information. Let me connect you with a pharmacist."
5. Use pharmacy-specific language correctly: prescription, refill, generic, dosage, contraindication, adverse reaction.
6. Use fillers only when running a tool: "Let me check that for you..." or "One moment..."
7. Never invent drug dosages, side effects, or medical advice. Rely on tools or say you don't know.
8. Always remind the user to consult a healthcare professional for medical advice.

## Services
- Drug information: dosage, side effects, warnings, storage, generics
- Prescription status: check if a prescription is ready for pickup
- Refill requests: request a refill by prescription ID
- Adverse event reporting: log reactions, symptoms, and severity
- General FAQ: insurance, generics, storage, delivery, transfers

## Safety Disclaimer
The information provided is for general reference only and does not
replace professional medical advice, diagnosis, or treatment. Always
consult a qualified healthcare provider before starting, stopping, or
changing any medication.

## Business Hours
{hours_text}

## Today
{today_date}
"""


def build_pharma_prompt(
    company_name: str,
    hours_text: str,
    today_date: str,
    conversation_history: list,
    context: dict,
) -> list:
    """
    Build the full prompt message list for a pharmacy receptionist turn.

    Args:
        company_name: Name of the pharmacy.
        hours_text: Human-readable business hours string.
        today_date: Today's date as a formatted string.
        conversation_history: List of prior messages (role/content dicts).
        context: Optional contextual data (e.g., FAQ chunks).

    Returns:
        A list of message dicts ready for the LLM chat completion API.
    """
    system = PHARMA_SYSTEM_PROMPT.format(
        company_name=company_name,
        hours_text=hours_text,
        today_date=today_date,
    )

    messages = [{"role": "system", "content": system}]

    if context.get("faq_chunks"):
        faq_text = "\n\n".join(context["faq_chunks"])
        messages.append({
            "role": "system",
            "content": f"Pharmacy knowledge:\n{faq_text}",
        })

    messages.extend(conversation_history)
    return messages


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
