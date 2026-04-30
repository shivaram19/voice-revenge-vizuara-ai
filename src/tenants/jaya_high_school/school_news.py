"""
Jaya High School — Upcoming School News & Events
==================================================
Tenant-owned list of events that are happening at the school in the
near future. The agent surfaces a curated 1-2 of these when the parent
accepts a post-intent news offer.

In production this list would refresh from the school's CMS / calendar
(via a separate ingestion job) into Redis with TTL. The in-process list
here is for dev + integration tests.

Why this layer is *separate* from parent records:
  - Parent records are personal, PII-bearing, change per parent.
  - School news is shared, public-facing, changes per term.
  Separating the two lets us update the news weekly without touching
  any parent's record, and prevents the LLM from confusing
  parent-specific data (Aarav's class) with school-wide data
  (Sports Day on Saturday).

Ref: ADR-014 (Voice Intent Framework); DFS-008 (intent specs).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class SchoolEvent:
    """A single event the school wants to communicate to parents."""

    event_id: str
    title: str           # short, human-readable: "Parent-Teacher Meeting"
    date: str            # ISO YYYY-MM-DD
    description: str     # 1-2 sentence agent-speakable summary
    audience: str        # "all" | "primary" | "secondary" | "class:8" | etc.
    priority: int        # 1 (highest) to 5 (lowest)
    requires_action: bool = False   # True if parent should do something


# Demo events — replace with CMS-fed list in production.
JAYA_SCHOOL_NEWS: List[SchoolEvent] = [
    SchoolEvent(
        event_id="ptm-may-2026",
        title="Parent-Teacher Meeting",
        date="2026-05-09",
        description=(
            "Our Parent-Teacher Meeting is on Saturday, May 9th, "
            "from 10 AM to 1 PM. Each class teacher will share "
            "your child's progress and discuss any concerns."
        ),
        audience="all",
        priority=1,
        requires_action=True,
    ),
    SchoolEvent(
        event_id="science-exhibition-2026",
        title="Science Exhibition",
        date="2026-05-23",
        description=(
            "The annual Science Exhibition is on May 23rd, from 9 AM. "
            "Students from classes 6 to 10 will present projects. "
            "Parents are warmly welcome."
        ),
        audience="secondary",
        priority=2,
    ),
    SchoolEvent(
        event_id="summer-vacation-2026",
        title="Summer Vacation",
        date="2026-05-30",
        description=(
            "Summer vacation begins May 30th. Classes resume on "
            "June 12th. The office will remain open between "
            "10 AM and 1 PM during the break."
        ),
        audience="all",
        priority=2,
    ),
    SchoolEvent(
        event_id="sports-day-2026",
        title="Annual Sports Day",
        date="2026-06-21",
        description=(
            "Annual Sports Day is on June 21st, beginning 7:30 AM. "
            "Each class will participate in track and group events. "
            "Refreshments will be served."
        ),
        audience="all",
        priority=2,
    ),
    SchoolEvent(
        event_id="board-exam-prep-class-10",
        title="Board Exam Preparation Sessions (Class 10)",
        date="2026-06-15",
        description=(
            "Extra preparation sessions for Class 10 board exams "
            "begin June 15th. Sessions run weekday evenings, "
            "5 PM to 7 PM. Attendance is recommended."
        ),
        audience="class:10",
        priority=1,
        requires_action=True,
    ),
]


def relevant_events_for(child_class: str, limit: int = 2) -> List[SchoolEvent]:
    """
    Return up to `limit` upcoming events most relevant to the child's
    class, sorted by priority then date. Audience filtering: events
    targeting "all" or matching the child's specific class are eligible.
    """
    if not child_class:
        return JAYA_SCHOOL_NEWS[:limit]

    # Best-effort class extraction: "Class 10 - A" → "10"
    class_num = ""
    for tok in child_class.split():
        if tok.isdigit():
            class_num = tok
            break

    def _matches(evt: SchoolEvent) -> bool:
        a = evt.audience.lower()
        if a == "all":
            return True
        if a == "primary" and class_num and 1 <= int(class_num) <= 5:
            return True
        if a == "secondary" and class_num and 6 <= int(class_num) <= 10:
            return True
        if a.startswith("class:") and class_num:
            return a.split(":", 1)[1] == class_num
        return False

    eligible = [e for e in JAYA_SCHOOL_NEWS if _matches(e)]
    eligible.sort(key=lambda e: (e.priority, e.date))
    return eligible[:limit]


def render_news_block(child_class: Optional[str], limit: int = 2) -> str:
    """
    Render the top relevant events as a prompt context block. The LLM
    uses this when the parent accepts a news offer; it is NOT injected
    when the parent has not yet been asked.
    """
    events = relevant_events_for(child_class or "", limit=limit)
    if not events:
        return ""
    lines = ["## SCHOOL NEWS — RELEVANT UPCOMING EVENTS"]
    for evt in events:
        action = " (action requested)" if evt.requires_action else ""
        lines.append(f"- {evt.title} ({evt.date}){action}: {evt.description}")
    lines.append(
        "Share at most TWO events naturally if the parent accepts the "
        "offer. Lead with the highest-priority item. Keep each turn "
        "≤18 words; let the parent decide whether to hear more."
    )
    return "\n".join(lines)


__all__ = [
    "SchoolEvent",
    "JAYA_SCHOOL_NEWS",
    "relevant_events_for",
    "render_news_block",
]
