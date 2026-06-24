"""
Healthcare Domain Plugin
========================
Implements DomainPort for the hospital patient follow-up vertical.
Wires tools, prompts, seed data, and the receptionist into a single
composition root that can be used by the standalone MVP app.

Goal-Engineering alignment:
  - Objective: capture well-being, medicine adherence, side effects,
    and escalation needs for post-visit patients.
  - Constraint: no diagnosis or medical advice; escalate emergencies;
    concise Telugu/English turns.
  - Toolset: patient lookup, symptom/adherence/side-effect recording,
    callback scheduling, escalation, and summary persistence.

Ref: docs/engineering/goal-vector-healthcare-mvp.md
     Cockburn 2005 (Hexagonal Architecture) [^42];
     Gamma et al. 1994 (Template Method) [^95].
"""

from __future__ import annotations

from typing import Any

from src.domains.healthcare_mvp.receptionist import HealthcareReceptionist
from src.domains.healthcare_mvp.seed import seed_healthcare_db
from src.domains.healthcare_mvp.tools import (
    EscalationTool,
    LookupPatientTool,
    RecordMedicineAdherenceTool,
    RecordSideEffectTool,
    RecordSymptomTool,
    SaveFollowUpSummaryTool,
    ScheduleFollowupTool,
)
from src.emotion.detector import EmotionDetector
from src.emotion.prompt_adapter import EmotionPromptAdapter
from src.infrastructure.interfaces import DomainPort, LLMPort
from src.receptionist.service import Receptionist, ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry


class HealthcareDomain(DomainPort):
    """Plugin entry-point for the healthcare patient follow-up vertical."""

    @property
    def domain_id(self) -> str:
        return "healthcare-patient-follow-up"

    def create_receptionist(
        self,
        llm_client: LLMPort,
        tts_provider: Any | None = None,
    ) -> Receptionist:
        """Factory: builds a fully-wired HealthcareReceptionist."""
        patients = seed_healthcare_db()["patients"]

        # Shared per-call buffers (tools are stateful by patient_id).
        symptom_tool = RecordSymptomTool()
        adherence_tool = RecordMedicineAdherenceTool()
        side_effect_tool = RecordSideEffectTool()
        schedule_tool = ScheduleFollowupTool()

        registry = ToolRegistry()
        registry.register(LookupPatientTool(patients))
        registry.register(symptom_tool)
        registry.register(adherence_tool)
        registry.register(side_effect_tool)
        registry.register(schedule_tool)
        registry.register(EscalationTool())
        registry.register(
            SaveFollowUpSummaryTool(
                symptom_tool=symptom_tool,
                adherence_tool=adherence_tool,
                side_effect_tool=side_effect_tool,
                schedule_tool=schedule_tool,
            )
        )

        config = self.get_config()

        return HealthcareReceptionist(
            config=config,
            tool_registry=registry,
            llm_client=llm_client,
            tts_provider=tts_provider,
            emotion_detector=EmotionDetector(),
            prompt_adapter=EmotionPromptAdapter(),
        )

    def get_config(self) -> ReceptionistConfig:
        """Domain-specific ReceptionistConfig for the follow-up MVP."""
        return ReceptionistConfig(
            company_name="Arogya Hospital",
            hours_text="Outpatient services Monday through Saturday, 8 AM to 8 PM. Emergency 24/7.",
            tool_timeout_seconds=5.0,
            fallback_after_misunderstandings=3,
        )


# References
# [^42]: Cockburn, A. (2005). Hexagonal Architecture. alistair.cockburn.us/hexagonal-architecture/.
# [^94]: Martin, R. C. (2002). Agile Software Development: Principles, Patterns, and Practices. Prentice Hall.
# [^95]: Gamma, E., et al. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
