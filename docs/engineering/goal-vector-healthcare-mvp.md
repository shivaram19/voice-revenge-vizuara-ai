# Goal Engineering: Healthcare Patient Follow-Up MVP

## What is Goal Engineering?

Goal engineering is the practice of defining, structuring, and refining AI objectives so they remain aligned with human intent, adaptable to context, and measurable in real-world performance. It moves beyond prompt engineering by designing the **outcomes** the AI should deliver, not just the inputs it receives.

A well-engineered goal is expressed as a **Goal Vector** with three components:

1. **Objective (The WHAT)** — the measurable outcome.
2. **Constraint (The HOW MUCH)** — guardrails, non-negotiables, and limits.
3. **Toolset (The WHERE/WITH)** — the APIs, tools, and data the agent may use.

This framing is supported by goal-oriented requirements engineering (van Lamsweerde, 2009) and recent work on autonomous goal-evolving agents (SAGA, 2025), which treat objectives as first-class artifacts that can be decomposed, measured, and refined [^1][^2].

---

## Goal Vector for the Healthcare Follow-Up Agent

### Objective

Complete a short, empathetic follow-up phone call with a recently discharged patient and capture:
- Patient well-being status (improving / same / worse / concerning).
- Medicine adherence (yes / no / partially / unsure).
- Reported symptoms and side effects.
- Any required escalation or callback.

Success is measured by:
- `follow_up_completion_rate` — % of connected calls that reach `save_follow_up_summary`.
- `data_capture_accuracy` — % of calls where well-being + adherence + side-effects are non-empty.
- `escalation_detection_rate` — % of serious symptoms correctly flagged.
- `patient_satisfaction_proxy` — no premature hang-ups due to robotic tone (measured via transcript review).

### Constraint

- Calls must stay under 3 minutes.
- Maximum 18 words per agent turn.
- Must speak in Telugu, English, or Telugu-English mix based on patient preference.
- Must never diagnose, prescribe, or give medical advice.
- Must escalate to emergency care immediately for serious symptoms.
- Must not hallucinate patient records or medicine details.
- Must obtain implicit consent ("Is this a good time?") before proceeding.

### Toolset

- `lookup_patient` — resolve patient by phone number.
- `record_symptom` — capture reported symptoms.
- `record_medicine_adherence` — capture adherence status.
- `record_side_effect` — capture side effects.
- `schedule_followup` — schedule callback or appointment reminder.
- `escalate_to_care_team` — flag urgent cases.
- `save_follow_up_summary` — persist structured outcome for dashboard.

---

## Engineering the Prompt

The system prompt in `src/domains/healthcare_mvp/prompts.py` is designed as a Goal Vector:

- **Objective** is stated in the first paragraph: check well-being and medicine adherence.
- **Constraints** are enumerated as numbered rules, including safety guardrails and turn-length limits.
- **Toolset** is listed explicitly so the LLM knows which actions it can take.
- **Measurable output** is enforced by requiring the agent to call `save_follow_up_summary` at the end of every call.

This structure makes the agent's behavior auditable and improvable against the KPIs above. Chung et al. (2000) show that treating non-functional requirements (constraints) as first-class goals is essential for building systems that are not just functional but also safe and usable in real organizations [^3].

---

## Why This Matters for the Hospital-Centered MVP

The hospital does not want a chatbot. It wants an agent that:
1. Reaches the right patient.
2. Collects reliable post-visit data.
3. Surfaces patients who need human attention.
4. Stores everything in a dashboard the care team can trust.

Goal engineering ensures the voice agent is optimized for these outcomes rather than for generic conversational fluency. Reward modeling research (DeepMind Crome, 2025) reinforces that agents must be measured against causally grounded quality drivers — such as factual accuracy and safety — rather than superficial metrics [^4].

---

## References

[^1]: van Lamsweerde, A. (2009). *Requirements Engineering: From System Goals to UML Models to Software Specifications*. John Wiley & Sons.

[^2]: SAGA Authors (2025). Accelerating Scientific Discovery with Autonomous Goal-evolving Agents. *arXiv:2512.21782*.

[^3]: Chung, L., Nixon, B., Yu, E., & Mylopoulos, J. (2000). *Non-Functional Requirements in Software Engineering*. Kluwer Academic Publishing.

[^4]: DeepMind (2025). Crome: Training models to focus on genuine quality drivers via causal and neutral augmentations. Reported improvements in Safety (+13.18%) and Reasoning (+7.19%) on RewardBench.
