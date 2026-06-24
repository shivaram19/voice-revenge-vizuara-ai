"""
Tests for Healthcare MVP prompt builder.

Verifies that the Goal-Engineering system prompt is assembled with:
  - Objective and constraint language
  - Patient context (name, diagnosis, medications)
  - Conversation history
"""

from src.domains.healthcare_mvp.prompts import (
    build_healthcare_instructions,
    build_healthcare_prompt,
)


def test_prompt_contains_goal_constraints():
    messages = build_healthcare_prompt(
        company_name="Arogya Hospital",
        hours_text="8 AM to 8 PM",
        today_date="Monday, June 23, 2026",
        conversation_history=[],
        context={},
    )
    assert len(messages) == 1
    system = messages[0]["content"]
    assert "Arogya Hospital" in system
    assert "Never diagnose" in system
    assert "escalate_to_care_team" in system
    assert "save_follow_up_summary" in system


def test_prompt_injects_patient_context():
    context = {
        "patient": {
            "name": "Ramesh Rao",
            "diagnosis": "Hypertension",
            "medications": [
                {
                    "name": "Telma H",
                    "dosage": "40 mg",
                    "frequency": "once daily",
                    "instructions": "after breakfast",
                }
            ],
        }
    }
    messages = build_healthcare_prompt(
        company_name="Arogya Hospital",
        hours_text="8 AM to 8 PM",
        today_date="Monday, June 23, 2026",
        conversation_history=[{"role": "user", "content": "Hello"}],
        context=context,
    )
    assert len(messages) == 2  # system + history
    system = messages[0]["content"]
    assert "Ramesh Rao" in system
    assert "Hypertension" in system
    assert "Telma H" in system
    assert messages[1] == {"role": "user", "content": "Hello"}


def test_prompt_short_turn_instruction():
    messages = build_healthcare_prompt(
        company_name="Arogya Hospital",
        hours_text="8 AM to 8 PM",
        today_date="Monday, June 23, 2026",
        conversation_history=[],
        context={},
    )
    system = messages[0]["content"]
    assert "Maximum 18 words per turn" in system


def test_build_healthcare_instructions():
    instructions = build_healthcare_instructions(
        company_name="Arogya Hospital",
        hours_text="8 AM to 8 PM",
        today_date="Monday, June 23, 2026",
        patient_context={
            "name": "Ramesh Rao",
            "diagnosis": "Hypertension",
            "medications": [
                {"name": "Telma H", "dosage": "40 mg", "frequency": "once daily", "instructions": ""}
            ],
        },
    )
    assert isinstance(instructions, str)
    assert "Arogya Hospital" in instructions
    assert "Ramesh Rao" in instructions
    assert "Never diagnose" in instructions
