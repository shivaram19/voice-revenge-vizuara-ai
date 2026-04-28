"""
Emotion Prompt Adapter — Inject emotional context into LLM system prompts.

Research Provenance:
    - IJISAE (2025): "Emotion-Specific Instructions" are critical;
      angry users need calm/respectful/concise reassurance, sad users
      need uplifting replies [^E8].
    - TechRxiv LLMSER: embedding emotion metadata directly into the LLM
      prompt enables dynamic tone, vocabulary, and sentence-structure
      adaptation [^E4].
    - Emotional Framing study (arXiv:2507.21083, 2025): GPT-4 exhibits
      "emotional rebound" — it counters negative user tone with softened
      positive responses. We explicitly override this via system prompt
      to maintain tone consistency [^E10].
    - SigArch (2026): system prompt length increases TTFT; emotion context
      must be compact (<50 tokens) [^E11].

[^E4]: TechRxiv. (2025). LLMSER: Emotion-Enhanced LLM Responses.
[^E8]: IJISAE. (2025). Emotion-Specific Instructions for LLM Prompt Engineering.
[^E10]: Emotional Framing Induces Bias in LLM Outputs. arXiv:2507.21083 (2025).
[^E11]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
"""

from __future__ import annotations

from typing import List, Dict

from src.emotion.profile import EmotionalTone


# Compact emotion-to-instruction mappings (<20 tokens each) [^E8][^E11]
# Each entry tells the LLM HOW to respond, not WHAT to say.
_EMOTION_INSTRUCTIONS: Dict[EmotionalTone, str] = {
    # [^E8]: Angry → calm, respectful, concise reassurance
    EmotionalTone.ANGRY: (
        "The caller is angry. Respond with calm, respectful brevity. "
        "Acknowledge their frustration. Offer a concrete solution. No filler."
    ),
    # [^E8]: Frustrated → patient, solution-focused
    EmotionalTone.FRUSTRATED: (
        "The caller is frustrated. Be patient and solution-focused. "
        "Validate their experience. Explain next steps clearly."
    ),
    # [^E8]: Urgent/Distressed → calm authority, immediate action
    EmotionalTone.URGENT: (
        "The caller has an urgent situation. Be calm, direct, and authoritative. "
        "Prioritize safety. Give one clear action immediately."
    ),
    EmotionalTone.DISTRESSED: (
        "The caller is distressed. Be grounding and reassuring. "
        "Speak slowly. Offer concrete help. Validate their feelings."
    ),
    # [^E8]: Confused → structured, step-by-step clarity
    EmotionalTone.CONFUSED: (
        "The caller is confused. Use simple, structured explanations. "
        "One step at a time. Confirm understanding after each point."
    ),
    # [^E8]: Rushed → brief, no preamble, bullet-style if possible
    EmotionalTone.RUSHED: (
        "The caller is in a hurry. Be extremely brief. "
        "No preamble. Give the answer in 10 words or less."
    ),
    # Tired → gentle pacing, offer assistance
    EmotionalTone.TIRED: (
        "The caller sounds tired. Be gentle and accommodating. "
        "Offer to handle details for them. Keep it short."
    ),
    # Grateful → mirror warmth, express appreciation
    EmotionalTone.GRATEFUL: (
        "The caller is grateful. Mirror their warmth. "
        "Express genuine appreciation. Offer any extra help."
    ),
    # Calm → default professional tone
    EmotionalTone.CALM: (
        "The caller is calm. Maintain a friendly, professional tone."
    ),
}

# Trajectory overrides: when pattern detected, prepend this instruction [^E5]
_TRAJECTORY_OVERRIDES: Dict[str, str] = {
    "ESCALATING": (
        "WARNING: Caller emotion is escalating across turns. "
        "De-escalate immediately. Slow down. Offer human transfer."
    ),
    "FLUCTUATING": (
        "Caller emotion is unstable. Stay consistent and calm. "
        "Do not mirror erratic tone."
    ),
}


class EmotionPromptAdapter:
    """
    Injects compact emotion instructions into LLM system prompts.

    Principle: The LLM already knows how to be empathetic; we just tell it
    WHEN and HOW via explicit, compact directives [^E8]. This avoids
    fine-tuning and keeps the system deterministic.
    """

    def __init__(self, max_context_tokens: int = 80):
        """
        Args:
            max_context_tokens: Budget for emotion context in system prompt [^E11].
        """
        self.max_context_tokens = max_context_tokens

    def adapt_prompt(
        self,
        base_system_prompt: str,
        detected_tone: EmotionalTone,
        trajectory_name: str = "STABLE",
        consecutive_negative: int = 0,
    ) -> str:
        """
        Augment a base system prompt with emotion-specific instructions.

        Returns the adapted prompt. Original prompt is preserved; emotion
        context is appended as a distinct section so it can be stripped
        for A/B testing or debugging [^E4].
        """
        instruction = _EMOTION_INSTRUCTIONS.get(detected_tone, _EMOTION_INSTRUCTIONS[EmotionalTone.CALM])

        parts: List[str] = [base_system_prompt]
        parts.append("")  # visual separator
        parts.append("## Emotional Context")
        parts.append(instruction)

        # [^E5]: Trajectory-aware override takes precedence over single-turn instruction
        if trajectory_name in _TRAJECTORY_OVERRIDES:
            parts.append(_TRAJECTORY_OVERRIDES[trajectory_name])

        # [^E9]: Consecutive negative turn counter as explicit signal
        if consecutive_negative >= 2:
            parts.append(
                f"Caller has expressed negative emotion for {consecutive_negative} consecutive turns."
            )

        adapted = "\n".join(parts)

        # [^E11]: Hard token budget enforcement (approximate: 1 token ≈ 0.75 English words)
        word_count = len(adapted.split())
        if word_count > self.max_context_tokens * 1.5:
            # Truncate emotion section to stay within budget
            adapted = base_system_prompt + "\n\n## Emotional Context\n" + instruction

        return adapted
