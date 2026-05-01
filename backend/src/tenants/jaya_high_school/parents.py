"""
Jaya High School — Parent Records (Tenant-Owned Seed)
======================================================
The seed list of verified parent records for Jaya High School. In
production these are populated from the school's billing system /
SIS via a separate ingestion process and live in Redis with TTL; the
in-process list here is for dev + integration tests.

Records here authoritatively answer: who is on the call, what is their
child's name and class, what is their fee status, when is the next
payment due, what notes do we have from prior contact.

Ref: DFS-007 (Suryapet parent demographic); "Parent data contract"
     project memory (2026-04-30).
"""

from __future__ import annotations

from typing import List

from src.domains.education.parent_registry import ParentRecord, PaymentEntry


JAYA_PARENT_RECORDS: List[ParentRecord] = [
    # Test record for the project owner's phone — exercises the
    # PAID_IN_FULL "supportive confirmation" path. This is the most
    # common production flow: most parents have already paid by the
    # time we call, and the agent's job is to confirm + thank.
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
            "Active member of the robotics club. "
            "Father pays via UPI; reachable evenings after 6 PM."
        ),
    ),
    # ---- Extend below with additional Jaya HS parents per term ----
    # Records can also be supplied at runtime via the JAYA_PARENT_REGISTRY
    # env var (JSON list); see ParentRegistry._record_from_dict.
]


__all__ = ["JAYA_PARENT_RECORDS"]
