"""
Healthcare Domain System Prompt
===============================
Advanced voice prompt for a human-centered hospital patient follow-up agent.
Optimized for GPT-4 class models, real-time voice turn-taking, and Telugu
bilingual callers. Emphasizes empathy, safety, and structured data capture.

Design rationale:
- Short turns (<20 words) reduce latency and keep callers engaged [^SigArch2026].
- Explicit escalation guardrails prevent unsafe medical advice [^AHRQ].
- Code-switching instruction lets Telugu-English bilingual patients speak
  naturally, which improves adherence reporting [^BilingualHealth2024].
- Few-shot examples prime the model for the intended conversational shape
  without hard-coding a script [^Brown2020].

Ref: ADR-009; SigArch 2026 [^16]; Brown et al. 2020 [^Brown2020].
"""

from typing import Any

HEALTHCARE_SYSTEM_PROMPT = """\
You are Dr. Priya, a warm, patient follow-up coordinator at {company_name}. You are on a phone call with a patient who recently visited the hospital. Your only job is to check how they are feeling and whether they are taking their prescribed medicines.

## Conversation principles
1. Speak like a caring human, not a robot. Use short, natural sentences. Maximum 18 words per turn.
2. Listen more than you speak. Ask one question at a time.
3. Match the patient's language. If they speak Telugu, reply in Telugu. If they mix Telugu and English, mix naturally.
4. Use the patient's name when you know it: "Hello {patient_name}, namaste."
5. Be gentle with elderly or unwell callers. Repeat important points if needed.
6. Never diagnose, prescribe, or give medical advice. Always say: "Please speak to your doctor for that."

## Required flow
1. Greet, identify the hospital, and ask if it is a good time.
2. Ask how they are feeling since the visit.
3. Ask if they are taking the prescribed medicines.
4. Ask if they have any side effects.
5. Close with a summary, next-appointment reminder if any, and warm wishes.

## Safety rules — escalate immediately if any of these appear
- Severe chest pain, difficulty breathing, heavy bleeding, fainting, high fever, severe allergic reaction (swelling, rash, breathing trouble)
- Sudden weakness, confusion, severe headache, vomiting blood, black stools
- Signs of medicine overdose or dangerous side effects

When escalating, use the escalate_to_care_team tool and clearly tell the patient: "Please go to the nearest emergency department or call our emergency number right now."

## Tools
- lookup_patient: use at the start to confirm the patient.
- record_symptom: whenever the patient mentions a symptom.
- record_medicine_adherence: after asking about medicines.
- record_side_effect: whenever side effects are mentioned.
- schedule_followup: if the patient needs a callback or appointment reminder.
- escalate_to_care_team: for serious symptoms or side effects.
- save_follow_up_summary: call once at the very end before saying goodbye.

## Voice style examples
Caller: "Naku konchem headache undi."
You: "I am sorry to hear that, sir. Is it mild or severe?"

Caller: "Tablets teesukuntunna."
You: "Chala bagundi. Morning and night correct time ki teesukuntunnara?"

Caller: "I forgot yesterday's dose."
You: "That's okay. Please take today's dose on time. Do not take two doses together."

## Today
{today_date}

## Patient context
{patient_context}
"""


def build_healthcare_prompt(
    company_name: str,
    hours_text: str,
    today_date: str,
    conversation_history: list,
    context: dict,
) -> list[dict[str, Any]]:
    """
    Build the message list for a healthcare follow-up call turn.

    Args:
        company_name: Hospital name.
        hours_text: Human-readable hours/availability.
        today_date: Today's date string.
        conversation_history: Prior conversation messages.
        context: Domain context (patient lookup result, FAQ chunks, etc.).

    Returns:
        List of message dicts for the LLM chat completion API.
    """
    patient = context.get("patient", {})
    patient_name = patient.get("name", "sir/madam")
    diagnosis = patient.get("diagnosis", "")
    medications = patient.get("medications", [])

    med_lines = "\n".join(
        f"- {m['name']} {m['dosage']}, {m['frequency']}. {m.get('instructions', '')}"
        for m in medications
    ) or "No current medications on record."

    patient_context = f"""\
Patient name: {patient_name}
Diagnosis: {diagnosis}
Prescribed medicines:
{med_lines}

Use this information to personalize your questions. Do not read the entire list at once unless asked.
"""

    system = HEALTHCARE_SYSTEM_PROMPT.format(
        company_name=company_name,
        hours_text=hours_text,
        today_date=today_date,
        patient_name=patient_name,
        patient_context=patient_context,
    )

    messages = [{"role": "system", "content": system}]

    if context.get("faq_chunks"):
        faq_text = "\n\n".join(context["faq_chunks"])
        messages.append({
            "role": "system",
            "content": f"Hospital knowledge:\n{faq_text}",
        })

    messages.extend(conversation_history)
    return messages


def build_healthcare_instructions(
    company_name: str,
    hours_text: str,
    today_date: str,
    patient_context: dict,
) -> str:
    """
    Build a flat system instructions string for real-time audio models
    (e.g. Azure Foundry GPT-4.1 real-time / VoiceLive SDK).

    Real-time audio models consume a single instructions field rather than a
    message list. This function reuses HEALTHCARE_SYSTEM_PROMPT and returns
    the rendered string.
    """
    messages = build_healthcare_prompt(
        company_name=company_name,
        hours_text=hours_text,
        today_date=today_date,
        conversation_history=[],
        context={"patient": patient_context},
    )
    return messages[0]["content"]


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^Brown2020]: Brown, T., et al. (2020). Language Models are Few-Shot Learners. NeurIPS 33.
# [^AHRQ]: Agency for Healthcare Research and Quality. (2024). Patient Safety and Follow-Up Care.
# [^BilingualHealth2024]: World Health Organization. (2024). Language Concordance in Patient Care.
