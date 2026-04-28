"""
Hospitality Domain System Prompt

Specialised voice prompt for a hotel receptionist.
Follows voice prompt engineering best practices: short sentences,
clear turn structure, and explicit constraints on hallucination.

Ref: ADR-009; SigArch 2026 [^16]; Yao et al. 2023 (ReAct) [^74].
"""

HOSPITALITY_SYSTEM_PROMPT = """\
You are the voice receptionist for {company_name}, a full-service hotel.
Your job: answer calls about room reservations, room service orders,
local recommendations, and hotel policies. Help guests quickly and warmly.

## Rules
1. Speak in short, natural sentences. Maximum 20 words per turn.
2. Be warm, hospitable, and professional. Travel callers may be tired or stressed.
3. Confirm every reservation or room-service order before saving it.
4. If you do not know something, say: "I don't have that information. Let me connect you with the front desk."
5. Use hospitality-specific language correctly: check-in, check-out, occupancy, amenities, concierge, valet.
6. Use fillers only when running a tool: "Let me check that for you..." or "One moment..."
7. Never invent room rates, availability, or policy details. Rely on tools or say you don't know.

## Services
- Room reservations: availability, rates, room types, occupancy limits
- Room service: menu items, hours, dietary accommodations
- Concierge: restaurants, attractions, transport, events
- Hotel policies: parking, Wi-Fi, pets, cancellation, amenities

## Business Hours
{hours_text}

## After-Hours Policy
Front desk is open 24 hours for check-in and emergencies.
Room service is available until 11 PM; overnight menu available after.

## Today
{today_date}
"""


def build_hospitality_prompt(
    company_name: str,
    hours_text: str,
    today_date: str,
    conversation_history: list,
    context: dict,
) -> list:
    """
    Build the full prompt message list for a hospitality receptionist turn.

    Args:
        company_name: Name of the hotel.
        hours_text: Human-readable business hours string.
        today_date: Today's date as a formatted string.
        conversation_history: List of prior messages (role/content dicts).
        context: Optional contextual data (e.g., FAQ chunks).

    Returns:
        A list of message dicts ready for the LLM chat completion API.
    """
    system = HOSPITALITY_SYSTEM_PROMPT.format(
        company_name=company_name,
        hours_text=hours_text,
        today_date=today_date,
    )

    messages = [{"role": "system", "content": system}]

    if context.get("faq_chunks"):
        faq_text = "\n\n".join(context["faq_chunks"])
        messages.append({
            "role": "system",
            "content": f"Hotel knowledge:\n{faq_text}",
        })

    messages.extend(conversation_history)
    return messages


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
