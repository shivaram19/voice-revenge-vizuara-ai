"""
AI Receptionist System Prompt
Ref: ADR-005; DFS-05 voice prompt engineering; SigArch 2026 streaming TTS.

Voice prompt engineering principles:
1. Conciseness: 10-20 words per turn reduces TTS latency and cognitive load.
   Citation: SigArch (2026), Section 4.5. Sentence buffering for streaming TTS
   demonstrates that shorter responses reduce perceived latency [^16].
2. Confirmation before mutation: Prevents errors in high-stakes bookings.
   Citation: Yao et al. (2023), ReAct. Tool execution requires validation
   loops to prevent incorrect actions [^12].
3. Latency masking fillers: "Let me check..." reduces perceived wait during
   tool execution by 200-400ms [^16].
4. Zero ambiguity: Clarity Manifesto prohibits hedging language in all
   system prompts .
"""

RECEPTIONIST_SYSTEM_PROMPT = """\
You are the voice receptionist for {company_name}.
Your job: answer calls, route callers, book appointments, answer FAQs, and take messages.

## Rules
1. Speak in short, natural sentences. Maximum 20 words per turn.
2. Be polite and professional.
3. Confirm every booking or message before saving it.
4. If you do not know something, say: "I don't have that information. Let me take a message."
5. Do not make up facts. Use the FAQ tool for company information.
6. If the caller asks for a human, offer to transfer or take a message.
7. Use fillers only when running a tool: "Let me check..." or "One moment..."

## Tools
- lookup_contact: Find a person or department.
- check_calendar: Check availability or book an appointment.
- search_faq: Answer questions about the company.
- take_message: Record a voicemail for someone.

## Business Hours
{hours_text}

## Today
{today_date}
"""

def build_prompt(
    company_name: str,
    hours_text: str,
    today_date: str,
    conversation_history: list,
    context: dict,
) -> list:
    """
    Build the full prompt for a receptionist turn.
    Ref: Qiu et al. (2026). VoiceAgentRAG inserts retrieved knowledge
    into system context to ground LLM responses [^14].
    """
    system = RECEPTIONIST_SYSTEM_PROMPT.format(
        company_name=company_name,
        hours_text=hours_text,
        today_date=today_date,
    )

    messages = [{"role": "system", "content": system}]

    # Add retrieved FAQ context if available
    # Citation: Lewis et al. (2020), RAG. Retrieved chunks augment
    # LLM context to reduce hallucination [^15].
    if context.get("faq_chunks"):
        faq_text = "\n\n".join(context["faq_chunks"])
        messages.append({
            "role": "system",
            "content": f"Retrieved company knowledge:\n{faq_text}",
        })

    # Add conversation history
    messages.extend(conversation_history)

    return messages

# References (module-level for traceability)
# [^12]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
# [^14]: Qiu, J., et al. (2026). VoiceAgentRAG. arXiv:2603.02206.
# [^15]: Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
