"""
Education Domain Plugin

Implements DomainPort for the education vertical. Wires together
config, tools, prompts, and the EducationReceptionist.

Ref: Cockburn 2005 (Hexagonal Architecture) [^42];
     Martin 2002 (OCP/DIP) [^94];
     Gamma et al. 1994 (Strategy Pattern) [^95];
     ADR-009: Domain-Modular Voice Agent Platform.
"""

from typing import Any, Optional

from src.infrastructure.interfaces import DomainPort, LLMPort
from src.receptionist.service import ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry
from src.domains.education.receptionist import EducationReceptionist
from src.domains.education.tools import (
    CourseLookupTool,
    CheckAdmissionStatusTool,
    ScheduleCampusVisitTool,
    FeeInquiryTool,
    FAQTool,
)
from src.domains.education.seed import seed_education_db


class EducationDomain(DomainPort):
    """
    Domain plugin for education institutions.

    Provides a fully wired receptionist capable of handling course
    inquiries, admissions status checks, campus visit scheduling,
    fee lookups, and FAQ search.
    """

    @property
    def domain_id(self) -> str:
        """Unique domain identifier."""
        return "education"

    def get_config(self) -> ReceptionistConfig:
        """
        Return domain-specific receptionist configuration.

        Returns:
            ReceptionistConfig tuned for an educational institution.
        """
        return ReceptionistConfig(
            company_name="Jaya High School, Suryapet",
            hours_text="Monday through Saturday, 8:30 AM to 4 PM. Sunday holiday.",
            max_turns=50,
            tool_timeout_seconds=3.0,
            fallback_after_misunderstandings=3,
        )

    def create_receptionist(
        self,
        llm_client: LLMPort,
        tts_provider: Optional[Any] = None,
    ) -> EducationReceptionist:
        """
        Factory: build an EducationReceptionist with all domain tools.

        Args:
            llm_client: An OpenAI-compatible LLM client.
            tts_provider: An optional TTS provider for streaming audio out.

        Returns:
            A fully configured EducationReceptionist instance.
        """
        config = self.get_config()
        db = seed_education_db()

        registry = ToolRegistry()
        registry.register(CourseLookupTool(courses=db["courses"]))
        registry.register(CheckAdmissionStatusTool(admissions=db["admissions"]))
        registry.register(ScheduleCampusVisitTool(existing_bookings=db["bookings"]))
        registry.register(FeeInquiryTool(courses=db["courses"]))
        registry.register(FAQTool(faqs=db["faqs"]))

        rec = EducationReceptionist(
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
