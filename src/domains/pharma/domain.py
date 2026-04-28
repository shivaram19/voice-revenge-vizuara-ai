"""
Pharma Domain Plugin

Implements DomainPort for the pharmacy vertical. Wires together
config, tools, prompts, and the PharmaReceptionist.

Ref: Cockburn 2005 (Hexagonal Architecture) [^42];
     Martin 2002 (OCP/DIP) [^94];
     Gamma et al. 1994 (Strategy Pattern) [^95];
     ADR-009: Domain-Modular Voice Agent Platform.
"""

from typing import Any, Optional

from src.infrastructure.interfaces import DomainPort, LLMPort
from src.receptionist.service import ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry
from src.domains.pharma.receptionist import PharmaReceptionist
from src.domains.pharma.tools import (
    DrugInfoTool,
    CheckPrescriptionStatusTool,
    RefillPrescriptionTool,
    ReportAdverseEventTool,
    FAQTool,
)
from src.domains.pharma.seed import seed_pharma_db


class PharmaDomain(DomainPort):
    """
    Domain plugin for pharmacy and pharmaceutical services.

    Provides a fully wired receptionist capable of handling drug
    information lookups, prescription status checks, refill requests,
    adverse event reporting, and FAQ search.
    """

    @property
    def domain_id(self) -> str:
        """Unique domain identifier."""
        return "pharma"

    def get_config(self) -> ReceptionistConfig:
        """
        Return domain-specific receptionist configuration.

        Returns:
            ReceptionistConfig tuned for a pharmacy.
        """
        return ReceptionistConfig(
            company_name="MediVoice Pharmacy",
            hours_text="Open 24 hours for prescription pickup. Pharmacy consultation 8 AM to 8 PM.",
            max_turns=50,
            tool_timeout_seconds=3.0,
            fallback_after_misunderstandings=3,
        )

    def create_receptionist(
        self,
        llm_client: LLMPort,
        tts_provider: Optional[Any] = None,
    ) -> PharmaReceptionist:
        """
        Factory: build a PharmaReceptionist with all domain tools.

        Args:
            llm_client: An OpenAI-compatible LLM client.
            tts_provider: An optional TTS provider for streaming audio out.

        Returns:
            A fully configured PharmaReceptionist instance.
        """
        config = self.get_config()
        db = seed_pharma_db()

        registry = ToolRegistry()
        registry.register(DrugInfoTool(drugs=db["drugs"]))
        registry.register(CheckPrescriptionStatusTool(prescriptions=db["prescriptions"]))
        registry.register(RefillPrescriptionTool(prescriptions=db["prescriptions"]))
        registry.register(ReportAdverseEventTool(adverse_events=db["adverse_events"]))
        registry.register(FAQTool(faqs=db["faqs"]))

        rec = PharmaReceptionist(
            config=config,
            tool_registry=registry,
            llm_client=llm_client,
            tts_provider=tts_provider,
        )

        return rec


# References
# [^42]: Cockburn, A. (2005). Hexagonal Architecture.
# [^94]: Martin, R. C. (2002). Agile Software Development, Principles, Patterns, and Practices. Prentice Hall.
# [^95]: Gamma, E., et al. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
