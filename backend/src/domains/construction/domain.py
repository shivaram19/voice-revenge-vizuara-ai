"""
Construction Domain Plugin
Implements DomainPort for the building-trades vertical.
OCP: registered as a plugin; no hardcoding in the pipeline.
Ref: Cockburn 2005 (Hexagonal Architecture) [^42];
     Martin 2002 (OCP/DIP) [^94];
     Gamma et al. 1994 (Strategy Pattern) [^95].
"""

from typing import Any, Optional

from src.infrastructure.interfaces import DomainPort, LLMPort
from src.receptionist.service import ReceptionistConfig
from src.receptionist.construction_service import ConstructionReceptionist
from src.receptionist.models import Database
from src.receptionist.tools.base import ToolRegistry
from src.receptionist.tools.faq import FAQKnowledgeBase, FAQChunk
from src.emotion.detector import EmotionDetector
from src.emotion.prompt_adapter import EmotionPromptAdapter

from .tools import (
    FindContractorTool,
    CheckAvailabilityTool,
    BookAppointmentTool,
    FAQTool,
    OutboundCallTool,
)
from .seed import seed_database, CONSTRUCTION_FAQ


class ConstructionDomain(DomainPort):
    """
    Plugin entry-point for the construction vertical.
    Wires tools, FAQ knowledge base, config, and emotion pipeline
    into a ConstructionReceptionist instance.
    """

    @property
    def domain_id(self) -> str:
        return "construction"

    async def create_receptionist(
        self,
        llm_client: LLMPort,
        tts_provider: Optional[Any] = None,
    ) -> ConstructionReceptionist:
        """
        Factory: builds a fully-wired ConstructionReceptionist.
        The pipeline injects llm_client; the domain supplies the rest.
        """
        # 1. Database & seed data
        db = Database(":memory:")
        await seed_database(db)

        # 2. FAQ knowledge base
        faq_kb = FAQKnowledgeBase()
        for item in CONSTRUCTION_FAQ:
            faq_kb.add(
                FAQChunk(
                    text=item["text"],
                    source="company_handbook",
                    category=item["category"],
                )
            )

        # 3. Tool registry (OCP: tools added without code changes)
        registry = ToolRegistry()
        registry.register(FindContractorTool(db))
        registry.register(CheckAvailabilityTool(db))
        registry.register(BookAppointmentTool(db))
        registry.register(FAQTool(faq_kb))
        registry.register(OutboundCallTool(db))

        # 4. Config
        config = self.get_config()

        # 5. Receptionist with emotion pipeline
        rec = ConstructionReceptionist(
            config=config,
            tool_registry=registry,
            llm_client=llm_client,
            tts_provider=tts_provider,
            emotion_detector=EmotionDetector(),
            prompt_adapter=EmotionPromptAdapter(),
        )

        return rec

    def get_config(self) -> ReceptionistConfig:
        """Domain-specific ReceptionistConfig."""
        return ReceptionistConfig(
            company_name="TreloLabs Voice AI",
            hours_text="Monday through Friday, 8 AM to 6 PM. Emergency dispatch 24/7.",
            tool_timeout_seconds=5.0,
        )


# References
# [^42]: Cockburn, A. (2005). Hexagonal Architecture. alistair.cockburn.us/hexagonal-architecture/.
# [^94]: Martin, R. C. (2002). Agile Software Development: Principles, Patterns, and Practices. Prentice Hall.
# [^95]: Gamma, E., et al. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
