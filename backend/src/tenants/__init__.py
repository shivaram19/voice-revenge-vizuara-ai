"""
Tenant Registry — Multi-School Identity & Data
================================================
Each *tenant* is a single school (or other client) deploying the voice
agent. A tenant owns:
  - Its school identity (name, address, hours, faculty)
  - Its parent records (current term enrolment, fees, payments, history)
  - Its scenario templates (fee-paid confirmation, partial reminder, etc.)

The DFS-007 patience profile is *regional*, not per-tenant — every
Suryapet school shares the same Telugu-speaking parent demographic — so
patience env vars are deployment-wide; tenants only differ in *content*.

The runtime resolves the active tenant at call start. By default this
is read from the `ACTIVE_TENANT_ID` env var; future revisions will
multi-tenant-route by the called Twilio number / Twilio phone-mapping.

Ref: ADR-009 (domain modularity); "Parent data contract" memory;
     user dialogue 2026-04-30 ("it varies from school to school but
     it's the same people").
"""

from __future__ import annotations

import os
from typing import Dict, Optional

from src.tenants.jaya_high_school.tenant import JAYA_HIGH_SCHOOL, Tenant


TENANTS: Dict[str, Tenant] = {
    JAYA_HIGH_SCHOOL.tenant_id: JAYA_HIGH_SCHOOL,
}


def get_active_tenant() -> Optional[Tenant]:
    """
    Return the tenant whose data should drive the current process.
    Falls back to Jaya High School (the only tenant today) if the env
    is unset.
    """
    tenant_id = os.getenv("ACTIVE_TENANT_ID", "jaya-suryapet")
    return TENANTS.get(tenant_id)


__all__ = ["TENANTS", "get_active_tenant", "Tenant", "JAYA_HIGH_SCHOOL"]
