"""
Pharma Receptionist — Thin Subclass
====================================
Delegates all ReAct orchestration to BaseReceptionist.
Only domain-specific behaviour: greeting text + prompt builder.

Ref: Gamma et al. 1994 (Template Method) [^95];
     Fowler 2018 (Remove Duplication) [^F1].
"""

from typing import List, Dict, Any

from src.receptionist.base_receptionist import BaseReceptionist
from src.receptionist.service import CallSession, ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry
from src.domains.pharma.prompts import build_pharma_prompt


class PharmaReceptionist(BaseReceptionist):
    """
    Concrete receptionist for the pharmacy domain.
    Integrates: tool registry + LLM client + TTS provider.
    """

    def _greeting_text(self) -> str:
        return (
            f"Thank you for calling {self.config.company_name}. "
            "I can help with drug information, prescription refills, or adverse event reporting. "
            "How may I assist you?"
        )

    def _build_messages(
        self,
        session: CallSession,
        today_date: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return build_pharma_prompt(
            company_name=self.config.company_name,
            hours_text=self.config.hours_text,
            today_date=today_date,
            conversation_history=session.conversation_history,
            context=context,
        )


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
# [^95]: Gamma, E., et al. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
