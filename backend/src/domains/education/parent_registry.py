"""
Parent Record Registry — Verified Records for Fee-Call Personalization
=======================================================================
Maps parent phone number → verified ParentRecord with child + fee details.
The voice agent injects the matched record into its system prompt at
call start so it can speak as a knowledgeable concierge, not a chatbot
probing for information.

Production wiring: a `ParentRecordPort` adapter pulls from the school
SIS / billing system. Dev/test override path: `JAYA_PARENT_REGISTRY`
env var (JSON list of records).

Ref: ADR-009 (domain modularity); ADR-013 (patience thresholds);
     "Parent data contract" project memory (2026-04-30).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class PaymentEntry:
    """A single fee payment posted to the parent's account."""

    amount_inr: int
    date: str           # ISO date YYYY-MM-DD
    method: str = "online"   # online | cash | cheque | dd
    reference: str = ""      # bank ref / receipt no.


@dataclass
class ParentRecord:
    """Verified record for the parent on the line."""

    phone: str                       # E.164
    salutation: str                  # "Mr." | "Mrs." | "Ms."
    parent_name: str                 # "Shiv Ram"
    child_name: str                  # "Aarav"
    child_class: str                 # "Class 8 - A"
    term_label: str                  # "April-September 2026"
    term_fee_total_inr: int          # 15000
    fee_due_date: str                # ISO date
    payments: List[PaymentEntry] = field(default_factory=list)
    language_preference: str = "English"   # "English" | "Telugu"
    notes: str = ""                  # free-form prior context

    @property
    def fee_paid_total_inr(self) -> int:
        return sum(p.amount_inr for p in self.payments)

    @property
    def fee_balance_inr(self) -> int:
        return max(0, self.term_fee_total_inr - self.fee_paid_total_inr)

    @property
    def status(self) -> str:
        """One of: PAID_IN_FULL, PARTIAL, UNPAID."""
        if self.fee_balance_inr == 0:
            return "PAID_IN_FULL"
        if self.fee_paid_total_inr > 0:
            return "PARTIAL"
        return "UNPAID"

    def to_prompt_block(self) -> str:
        """
        Render a verified-context block for the LLM system prompt.
        The agent is INSTRUCTED to treat this as ground truth and
        speak supportively from it — not to "look it up" via tools.
        """
        last_payment = self.payments[-1] if self.payments else None
        lines = [
            "## VERIFIED PARENT RECORD (treat as ground truth)",
            f"- Parent: {self.salutation} {self.parent_name}",
            f"- Child: {self.child_name} ({self.child_class})",
            f"- Term: {self.term_label}",
            f"- Term fee total: ₹{self.term_fee_total_inr:,}",
            f"- Paid so far: ₹{self.fee_paid_total_inr:,}",
            f"- Balance: ₹{self.fee_balance_inr:,}",
            f"- Due date: {self.fee_due_date}",
            f"- Status: {self.status}",
            f"- Preferred language: {self.language_preference}",
        ]
        if last_payment:
            lines.append(
                f"- Last payment: ₹{last_payment.amount_inr:,} on "
                f"{last_payment.date} ({last_payment.method})"
            )
        if self.notes:
            lines.append(f"- Notes: {self.notes}")

        # Status-driven guidance the LLM should follow
        if self.status == "PAID_IN_FULL":
            lines.append(
                "\n**Posture for this call:** SUPPORTIVE confirmation. "
                "The parent has paid in full. Open by acknowledging the "
                "child by name, confirm the fee is settled, and thank "
                "them. Do NOT ask for payment. Do NOT pitch new courses "
                "unless the parent asks. Close warmly within ~3 turns."
            )
        elif self.status == "PARTIAL":
            lines.append(
                f"\n**Posture for this call:** GENTLE reminder. "
                f"₹{self.fee_balance_inr:,} of ₹{self.term_fee_total_inr:,} "
                f"is outstanding. Acknowledge the partial payment with "
                f"thanks, mention the balance and due date once, ask if "
                f"the parent has questions or needs an installment plan. "
                f"Never threaten or imply consequence."
            )
        else:  # UNPAID
            lines.append(
                f"\n**Posture for this call:** PATIENT inquiry. "
                f"The fee for this term is not yet paid. Open by asking "
                f"if the parent received the previous reminder and "
                f"whether there are questions about the fee schedule or "
                f"payment options. Never pressure."
            )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Built-in dev/demo records — production replaces this with a port adapter.
# ---------------------------------------------------------------------------

_BUILTIN_RECORDS: List[ParentRecord] = [
    # Test record for the project owner's phone — exercises the
    # PAID_IN_FULL "supportive" path which is the most common in
    # production (most parents have paid by the time we call).
    ParentRecord(
        phone="+918919230290",
        salutation="Mr.",
        parent_name="Shiv Ram",
        child_name="Aarav",
        child_class="Class 8 - A",
        term_label="April-September 2026",
        term_fee_total_inr=15000,
        fee_due_date="2026-04-15",
        payments=[
            PaymentEntry(
                amount_inr=15000,
                date="2026-04-10",
                method="online",
                reference="TXN-2026041000942",
            ),
        ],
        language_preference="English",
        notes=(
            "Aarav scored 92% in last term exams. "
            "Active member of the robotics club."
        ),
    ),
]


class ParentRegistry:
    """
    Phone-keyed lookup for verified parent records.
    Lookups are tolerant to whitespace and formatting variations.
    """

    def __init__(self, records: Optional[List[ParentRecord]] = None) -> None:
        self._by_phone: dict[str, ParentRecord] = {}
        for record in (records if records is not None else _BUILTIN_RECORDS):
            self._by_phone[self._normalise(record.phone)] = record

        env_records = os.getenv("JAYA_PARENT_REGISTRY", "").strip()
        if env_records:
            try:
                payload = json.loads(env_records)
                if isinstance(payload, list):
                    for entry in payload:
                        rec = self._record_from_dict(entry)
                        if rec is not None:
                            self._by_phone[self._normalise(rec.phone)] = rec
            except (json.JSONDecodeError, TypeError, ValueError):
                # Malformed env override — silently ignore; the built-in
                # records still work. A telemetry warning would be ideal
                # but avoiding circular import with logging here.
                pass

    @staticmethod
    def _normalise(phone: str) -> str:
        """E.164-friendly normalization: strip spaces/dashes, ensure leading +."""
        if not phone:
            return ""
        cleaned = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        if cleaned and not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        return cleaned

    @staticmethod
    def _record_from_dict(entry: dict) -> Optional[ParentRecord]:
        """Build a ParentRecord from a JSON dict (env override path)."""
        try:
            payments_raw = entry.pop("payments", []) if "payments" in entry else []
            payments = [PaymentEntry(**p) for p in payments_raw]
            return ParentRecord(payments=payments, **entry)
        except (TypeError, ValueError):
            return None

    def lookup(self, phone: str) -> Optional[ParentRecord]:
        """Return the parent record for `phone`, or None if not found."""
        if not phone:
            return None
        return self._by_phone.get(self._normalise(phone))

    def all_records(self) -> List[ParentRecord]:
        return list(self._by_phone.values())


# References
# - ADR-009: Domain-modular voice agent platform.
# - ADR-013: Patience-aware conversation thresholds.
# - DFS-007: Suryapet parent demographic.
