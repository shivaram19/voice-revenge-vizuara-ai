"""
Healthcare Receptionist — Patient Follow-Up
============================================
Thin subclass of BaseReceptionist for hospital patient follow-up calls.
Loads the patient record at call start and injects it into every prompt.

Ref: ADR-009 (Domain Modularity); Gamma et al. 1994 (Template Method) [^95].
"""

from typing import Any

from src.domains.healthcare_mvp.prompts import build_healthcare_prompt
from src.domains.healthcare_mvp.seed import Patient, seed_healthcare_db
from src.receptionist.base_receptionist import BaseReceptionist
from src.receptionist.service import CallSession


class HealthcareReceptionist(BaseReceptionist):
    """
    Concrete receptionist for healthcare patient follow-up.
    """

    def __init__(self, *args, patient: Patient | None = None, **kwargs) -> None:
        self.patient = kwargs.pop("patient", patient)
        super().__init__(*args, **kwargs)
        self._patients = seed_healthcare_db()["patients"]

    async def handle_call_start(self, session_id: str, caller: str, called: str) -> str:
        """Look up patient by phone, then return the domain greeting."""
        self.patient = self._patients.get(caller)
        return await super().handle_call_start(session_id, caller, called)

    def _greeting_text(self) -> str:
        if self.patient is None:
            return (
                f"Hello, namaste. This is Dr. Priya calling from {self.config.company_name}. "
                "I am calling to check on your well-being after your recent visit. Is this a good time to talk?"
            )
        name = self.patient.name.split()[0]
        greeting = f"Hello {name}, namaste. This is Dr. Priya calling from {self.config.company_name}."
        if self.patient.language_preference.startswith("te"):
            return (
                f"Namaste {name} garu, nenu {self.config.company_name} nunchi Dr. Priya matladutunna. "
                "Meero kuda mee arogyam gurinchi check cheskundam ani call chesanu. Ippudu matladatam convenience aa?"
            )
        return (
            f"{greeting} I am calling to check on your well-being after your recent visit. "
            "Is this a good time to talk?"
        )

    def _build_messages(
        self,
        session: CallSession,
        today_date: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if self.patient is not None:
            context["patient"] = {
                "patient_id": self.patient.patient_id,
                "name": self.patient.name,
                "age": self.patient.age,
                "language_preference": self.patient.language_preference,
                "diagnosis": self.patient.diagnosis,
                "medications": [
                    {
                        "name": m.name,
                        "dosage": m.dosage,
                        "frequency": m.frequency,
                        "instructions": m.instructions,
                    }
                    for m in self.patient.medications
                ],
            }
        else:
            context["patient"] = {"name": "sir/madam"}
        return build_healthcare_prompt(
            company_name=self.config.company_name,
            hours_text=self.config.hours_text,
            today_date=today_date,
            conversation_history=session.conversation_history,
            context=context,
        )


# References
# [^95]: Gamma, E., et al. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
