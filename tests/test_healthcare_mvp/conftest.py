"""
Shared test fixtures for the Healthcare MVP.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.domains.healthcare_mvp.domain import HealthcareDomain
from src.domains.healthcare_mvp.seed import (
    clear_follow_up_records,
    set_follow_up_log_path,
)
from src.infrastructure.interfaces import LLMPort


class MockLLMClient(LLMPort):
    """
    Deterministic LLM client for unit tests.

    The test can pre-register responses or tool_calls by call index, or
    provide a callable that inspects the messages/tools and returns a result.
    """

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self.responses = responses or []
        self.call_index = 0
        self.calls: list[tuple] = []

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        self.calls.append((messages, tools))
        if self.call_index < len(self.responses):
            response = self.responses[self.call_index]
            self.call_index += 1
            return response
        # Default: echo the last user message as a direct response.
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg.get("content", "")
                break
        return {"content": f"Acknowledged: {last_user}"}

    def add_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        """Helper to queue a tool-call response."""
        self.responses.append({
            "content": None,
            "tool_calls": [{
                "id": f"call_{self.call_index}",
                "function": {"name": name, "arguments": json.dumps(arguments)},
            }],
        })


@pytest.fixture
def mock_llm():
    return MockLLMClient()


@pytest.fixture
def healthcare_domain(mock_llm):
    domain = HealthcareDomain()
    return domain.create_receptionist(llm_client=mock_llm)


@pytest.fixture(autouse=True)
def reset_follow_ups(tmp_path):
    """Reset in-memory follow-up records and point JSONL log to a temp file."""
    clear_follow_up_records()
    set_follow_up_log_path(str(tmp_path / "follow_ups.jsonl"))
    yield
    clear_follow_up_records()
