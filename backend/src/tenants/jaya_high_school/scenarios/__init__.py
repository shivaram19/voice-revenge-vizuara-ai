"""
Jaya High School — Scenario Templates
======================================
Each scenario is a posture-and-objective template the agent uses for
a specific kind of call. The same parent demographic + same regional
patience profile applies; what differs across scenarios is the
*reason for calling* and the conversational arc.

Naming convention: ``{intent}_{stance}.py`` — e.g. ``fee_paid_confirmation``.

Each scenario module exports a ``SCENARIO`` constant of type
:class:`Scenario` (defined in ``base.py``). The active scenario for a
call is resolved by :func:`pick_scenario` based on the parent record.

Ref: ADR-013 (patience thresholds); user dialogue 2026-04-30
     ("templates that would be for different domains how we should
     be responding").
"""

from src.tenants.jaya_high_school.scenarios.base import (
    Scenario,
    pick_scenario,
)
from src.tenants.jaya_high_school.scenarios.fee_paid_confirmation import (
    SCENARIO as FEE_PAID_CONFIRMATION,
)
from src.tenants.jaya_high_school.scenarios.fee_partial_reminder import (
    SCENARIO as FEE_PARTIAL_REMINDER,
)
from src.tenants.jaya_high_school.scenarios.fee_overdue_inquiry import (
    SCENARIO as FEE_OVERDUE_INQUIRY,
)
from src.tenants.jaya_high_school.scenarios.admission_inquiry import (
    SCENARIO as ADMISSION_INQUIRY,
)
from src.tenants.jaya_high_school.scenarios.attendance_followup import (
    SCENARIO as ATTENDANCE_FOLLOWUP,
)


SCENARIOS = {
    FEE_PAID_CONFIRMATION.scenario_id: FEE_PAID_CONFIRMATION,
    FEE_PARTIAL_REMINDER.scenario_id: FEE_PARTIAL_REMINDER,
    FEE_OVERDUE_INQUIRY.scenario_id: FEE_OVERDUE_INQUIRY,
    ADMISSION_INQUIRY.scenario_id: ADMISSION_INQUIRY,
    ATTENDANCE_FOLLOWUP.scenario_id: ATTENDANCE_FOLLOWUP,
}


__all__ = [
    "Scenario",
    "SCENARIOS",
    "pick_scenario",
    "FEE_PAID_CONFIRMATION",
    "FEE_PARTIAL_REMINDER",
    "FEE_OVERDUE_INQUIRY",
    "ADMISSION_INQUIRY",
    "ATTENDANCE_FOLLOWUP",
]
