"""
Hospitality Domain Plugin

Implements DomainPort for the hospitality vertical. Wires together
config, tools, prompts, and the HospitalityReceptionist.

Ref: Cockburn 2005 (Hexagonal Architecture) [^42];
     Martin 2002 (OCP/DIP) [^94];
     Gamma et al. 1994 (Strategy Pattern) [^95];
     ADR-009: Domain-Modular Voice Agent Platform.
"""

from typing import Any, Optional

from src.infrastructure.interfaces import DomainPort
from src.receptionist.service import ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry
from src.domains.hospitality.receptionist import HospitalityReceptionist
from src.domains.hospitality.tools import (
    CheckRoomAvailabilityTool,
    BookReservationTool,
    RoomServiceTool,
    ConciergeTool,
    FAQTool,
)
from src.domains.hospitality.seed import seed_hospitality_db


class HospitalityDomain(DomainPort):
    """
    Domain plugin for hospitality institutions.

    Provides a fully wired receptionist capable of handling room
    reservations, room service orders, concierge recommendations,
    and FAQ search.
    """

    @property
    def domain_id(self) -> str:
        """Unique domain identifier."""
        return "hospitality"

    def get_config(self) -> ReceptionistConfig:
        """
        Return domain-specific receptionist configuration.

        Returns:
            ReceptionistConfig tuned for a full-service hotel.
        """
        return ReceptionistConfig(
            company_name="Grand Voice Hotel",
            hours_text="Front desk open 24 hours. Check-in from 3 PM. Check-out by 11 AM.",
            max_turns=50,
            tool_timeout_seconds=3.0,
            fallback_after_misunderstandings=3,
        )

    def create_receptionist(
        self,
        llm_client: Any,
        tts_provider: Optional[Any] = None,
    ) -> HospitalityReceptionist:
        """
        Factory: build a HospitalityReceptionist with all domain tools.

        Args:
            llm_client: An OpenAI-compatible LLM client.
            tts_provider: An optional TTS provider for streaming audio out.

        Returns:
            A fully configured HospitalityReceptionist instance.
        """
        config = self.get_config()
        db = seed_hospitality_db()

        registry = ToolRegistry()
        registry.register(CheckRoomAvailabilityTool(
            rooms=db["rooms"],
            bookings=db["bookings"],
        ))
        registry.register(BookReservationTool(
            rooms=db["rooms"],
            bookings=db["bookings"],
        ))
        registry.register(RoomServiceTool(menu=db["menu"]))
        registry.register(ConciergeTool(recommendations=db["recommendations"]))
        registry.register(FAQTool(faqs=db["faqs"]))

        rec = HospitalityReceptionist(
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
