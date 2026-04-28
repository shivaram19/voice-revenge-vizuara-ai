"""
Pharma-specific tools for the voice receptionist.

Each tool is self-contained: schema definition, execution, and voice-friendly
formatting. Tools operate on in-memory mock data so the domain can be
exercised without external dependencies.

Ref: OpenAI Function Calling API [^13]; ADR-009.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.receptionist.tools.base import Tool, ToolResult
from src.domains.pharma.seed import (
    PHARMA_DRUGS,
    PHARMA_PRESCRIPTIONS,
    PHARMA_FAQ,
    DrugRecord,
    PrescriptionRecord,
    AdverseEventRecord,
)


# ---------------------------------------------------------------------------
# Drug Information Tool
# ---------------------------------------------------------------------------

class DrugInfoTool(Tool):
    """
    Lookup drug information by name.

    Returns dosage instructions, common side effects, warnings, and
    storage guidance. Production: integrate with FDA Drug Labels API
    or a clinical decision support system (e.g., First DataBank).
    """

    def __init__(self, drugs: Optional[List[DrugRecord]] = None):
        self._drugs = drugs or list(PHARMA_DRUGS)

    @property
    def name(self) -> str:
        return "drug_info"

    @property
    def description(self) -> str:
        return (
            "Look up medication information by brand or generic name. "
            "Returns dosage, side effects, warnings, and storage instructions."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "drug_name": {
                    "type": "string",
                    "description": "Brand or generic name of the medication, e.g., Aspirin or Metformin.",
                },
            },
            "required": ["drug_name"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        drug_name = kwargs.get("drug_name", "").lower()
        if not drug_name:
            return ToolResult(
                success=False,
                message="Please provide the name of the medication you'd like information about.",
                error="missing_drug_name",
            )

        match = next(
            (d for d in self._drugs if drug_name in d.name.lower() or drug_name in d.generic_name.lower()),
            None,
        )

        if not match:
            return ToolResult(
                success=False,
                message=f"I couldn't find information for '{drug_name}'. Would you like to speak with a pharmacist?",
                error="drug_not_found",
            )

        side_effects = ", ".join(match.side_effects)
        warnings = " ".join(match.warnings)
        message = (
            f"{match.name} — {match.generic_name}. "
            f"Dosage: {match.dosage} "
            f"Common side effects include: {side_effects}. "
            f"Important warnings: {warnings} "
            f"Storage: {match.storage} "
            "Always consult a healthcare professional before making any medication decisions."
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "name": match.name,
                "generic_name": match.generic_name,
                "dosage": match.dosage,
                "side_effects": match.side_effects,
                "warnings": match.warnings,
                "category": match.category,
                "storage": match.storage,
            },
        )


# ---------------------------------------------------------------------------
# Check Prescription Status Tool
# ---------------------------------------------------------------------------

class CheckPrescriptionStatusTool(Tool):
    """
    Check whether a prescription is ready for pickup.

    Searches by prescription ID or patient name. Production: integrate
    with pharmacy management system (e.g., McKesson Connect, PioneerRx).
    """

    def __init__(self, prescriptions: Optional[List[PrescriptionRecord]] = None):
        self._prescriptions = prescriptions or list(PHARMA_PRESCRIPTIONS)

    @property
    def name(self) -> str:
        return "check_prescription_status"

    @property
    def description(self) -> str:
        return (
            "Check the status of a prescription by prescription ID or patient name. "
            "Returns whether it is ready, in process, delayed, or pending."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "prescription_id": {
                    "type": "string",
                    "description": "The prescription ID, e.g., RX-2026-1001.",
                },
                "patient_name": {
                    "type": "string",
                    "description": "The patient's full name, e.g., Alice Johnson.",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs) -> ToolResult:
        prescription_id = kwargs.get("prescription_id", "").strip()
        patient_name = kwargs.get("patient_name", "").strip().lower()

        if not prescription_id and not patient_name:
            return ToolResult(
                success=False,
                message="Please provide a prescription ID or patient name so I can check the status.",
                error="missing_query",
            )

        matches: List[PrescriptionRecord] = []
        for p in self._prescriptions:
            if prescription_id and p.prescription_id.lower() == prescription_id.lower():
                matches.append(p)
            elif patient_name and patient_name in p.patient_name.lower():
                matches.append(p)

        if not matches:
            return ToolResult(
                success=False,
                message="I couldn't find a prescription with that information. Please double-check the ID or name.",
                error="not_found",
            )

        lines: List[str] = []
        for p in matches[:3]:
            lines.append(
                f"Prescription {p.prescription_id} for {p.patient_name}: status is {p.status}. "
                f"{p.notes}"
            )
        message = " ".join(lines)
        return ToolResult(
            success=True,
            message=message,
            data={"matches": [self._prescription_to_dict(p) for p in matches]},
        )

    @staticmethod
    def _prescription_to_dict(p: PrescriptionRecord) -> Dict[str, Any]:
        return {
            "prescription_id": p.prescription_id,
            "patient_name": p.patient_name,
            "drug_name": p.drug_name,
            "status": p.status,
            "refills_remaining": p.refills_remaining,
            "total_refills": p.total_refills,
            "prescribed_date": p.prescribed_date,
            "last_filled_date": p.last_filled_date,
            "notes": p.notes,
        }


# ---------------------------------------------------------------------------
# Refill Prescription Tool
# ---------------------------------------------------------------------------

class RefillPrescriptionTool(Tool):
    """
    Request a prescription refill by prescription ID.

    Checks whether the prescription is refillable and updates the
    refill count. Production: integrate with pharmacy management system.
    """

    def __init__(self, prescriptions: Optional[List[PrescriptionRecord]] = None):
        self._prescriptions = prescriptions or list(PHARMA_PRESCRIPTIONS)

    @property
    def name(self) -> str:
        return "refill_prescription"

    @property
    def description(self) -> str:
        return (
            "Request a refill for an existing prescription using its prescription ID. "
            "Confirms that refills remain before processing."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "prescription_id": {
                    "type": "string",
                    "description": "The prescription ID to refill, e.g., RX-2026-1001.",
                },
            },
            "required": ["prescription_id"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        prescription_id = kwargs.get("prescription_id", "").strip()
        if not prescription_id:
            return ToolResult(
                success=False,
                message="Please provide the prescription ID you'd like to refill.",
                error="missing_prescription_id",
            )

        record = next(
            (p for p in self._prescriptions if p.prescription_id.lower() == prescription_id.lower()),
            None,
        )

        if not record:
            return ToolResult(
                success=False,
                message=f"I couldn't find prescription {prescription_id}. Please check the ID and try again.",
                error="prescription_not_found",
            )

        if record.refills_remaining <= 0:
            return ToolResult(
                success=False,
                message=(
                    f"Prescription {prescription_id} has no refills remaining. "
                    "Please contact your prescriber for a new prescription."
                ),
                error="no_refills",
            )

        # Simulate refill processing
        record.refills_remaining -= 1
        record.last_filled_date = datetime.utcnow().strftime("%Y-%m-%d")
        record.status = "in_process"

        return ToolResult(
            success=True,
            message=(
                f"Refill request for {prescription_id} has been submitted. "
                f"It should be ready within 2 hours. "
                f"You now have {record.refills_remaining} refill{'s' if record.refills_remaining != 1 else ''} remaining."
            ),
            data={
                "prescription_id": record.prescription_id,
                "refills_remaining": record.refills_remaining,
                "status": record.status,
            },
        )


# ---------------------------------------------------------------------------
# Report Adverse Event Tool
# ---------------------------------------------------------------------------

class ReportAdverseEventTool(Tool):
    """
    Log an adverse drug reaction report.

    Captures drug name, symptoms, and severity. Production: submit to
    FDA MedWatch or pharmacovigilance database.
    """

    def __init__(self, adverse_events: Optional[List[AdverseEventRecord]] = None):
        self._adverse_events = adverse_events or []
        self._counter = len(self._adverse_events)

    @property
    def name(self) -> str:
        return "report_adverse_event"

    @property
    def description(self) -> str:
        return (
            "Log an adverse drug reaction report. Requires drug name, symptoms, "
            "and severity. Provide a confirmation to the caller."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "drug_name": {
                    "type": "string",
                    "description": "Name of the medication involved in the adverse reaction.",
                },
                "symptoms": {
                    "type": "string",
                    "description": "Description of the symptoms experienced, e.g., rash, nausea, dizziness.",
                },
                "severity": {
                    "type": "string",
                    "enum": ["mild", "moderate", "severe"],
                    "description": "Severity of the reaction: mild, moderate, or severe.",
                },
            },
            "required": ["drug_name", "symptoms", "severity"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        drug_name = kwargs.get("drug_name", "").strip()
        symptoms_raw = kwargs.get("symptoms", "").strip()
        severity = kwargs.get("severity", "").strip().lower()

        if not drug_name or not symptoms_raw or not severity:
            return ToolResult(
                success=False,
                message="I need the drug name, symptoms, and severity to log the adverse event report.",
                error="missing_fields",
            )

        if severity not in ("mild", "moderate", "severe"):
            return ToolResult(
                success=False,
                message="Severity must be mild, moderate, or severe. Please specify one of these.",
                error="invalid_severity",
            )

        self._counter += 1
        report_id = f"AE-{datetime.utcnow().strftime('%Y%m%d')}-{self._counter:04d}"
        symptoms_list = [s.strip() for s in symptoms_raw.split(",") if s.strip()]

        event = AdverseEventRecord(
            report_id=report_id,
            drug_name=drug_name,
            symptoms=symptoms_list,
            severity=severity,
            reported_at=datetime.utcnow().isoformat(),
        )
        self._adverse_events.append(event)

        if severity == "severe":
            advice = " Because you reported a severe reaction, please seek emergency medical attention immediately."
        else:
            advice = " Please follow up with your healthcare provider if symptoms worsen."

        return ToolResult(
            success=True,
            message=(
                f"Adverse event report {report_id} has been logged for {drug_name}. "
                f"Symptoms recorded: {', '.join(symptoms_list)}. Severity: {severity}.{advice}"
            ),
            data={
                "report_id": report_id,
                "drug_name": drug_name,
                "symptoms": symptoms_list,
                "severity": severity,
            },
        )


# ---------------------------------------------------------------------------
# FAQ Search Tool
# ---------------------------------------------------------------------------

class FAQTool(Tool):
    """
    Search the pharmacy FAQ knowledge base.

    Uses simple keyword matching. Production: upgrade to FAISS semantic
    search per ADR-003 [^14][^37].
    """

    def __init__(self, faqs: Optional[List[Dict[str, str]]] = None):
        self._faqs = faqs or list(PHARMA_FAQ)

    @property
    def name(self) -> str:
        return "search_faq"

    @property
    def description(self) -> str:
        return (
            "Search the pharmacy knowledge base for answers about insurance, "
            "generics, storage, hours, delivery, transfers, and medication use."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The caller's question or keywords to search for.",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "").lower()
        if not query:
            return ToolResult(
                success=False,
                message="What would you like to know?",
                error="missing_query",
            )

        query_words = set(re.findall(r"\b\w+\b", query))
        scored: List[tuple] = []

        for faq in self._faqs:
            text = f"{faq['question']} {faq['answer']}".lower()
            text_words = set(re.findall(r"\b\w+\b", text))
            score = len(query_words & text_words)
            if score > 0:
                scored.append((score, faq))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:1]

        if not top:
            return ToolResult(
                success=False,
                message="I don't have that information right now. I can connect you with a pharmacist.",
                error="no_faq_match",
            )

        answer = top[0][1]["answer"]
        # Truncate to two sentences for voice brevity [^16]
        sentences = re.split(r"[.!?]+\s+", answer)
        voice_answer = ". ".join(sentences[:2]).strip()
        if voice_answer and not voice_answer.endswith("."):
            voice_answer += "."

        return ToolResult(
            success=True,
            message=voice_answer,
            data={"question": top[0][1]["question"], "answer": answer},
        )


# References
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^14]: Qiu, J., et al. (2026). VoiceAgentRAG. arXiv:2603.02206.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^37]: Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.
