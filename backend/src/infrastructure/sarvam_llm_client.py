"""
Sarvam AI LLM Client
=====================
OpenAI-compatible chat completions via Sarvam AI's API endpoint.
Drop-in replacement for AzureOpenAILLMClient for Indian-language deployments
that don't have Azure OpenAI configured.

API:
    POST https://api.sarvam.ai/v1/chat/completions
    Header: Authorization: Bearer <SARVAM_API_KEY>
    Body:   OpenAI-compatible chat completions request
    Model:  sarvam-m (multilingual, 22 Indian languages)

Why Sarvam LLM for Telugu:
    - sarvam-m is pretrained on Telugu, Hindi, and 20 other Indian languages.
    - Handles Tenglish (Telugu+English code-switching) natively.
    - API is OpenAI-compatible — same request/response schema.
    - No Azure subscription required.

Ref: Sarvam AI LLM docs (https://docs.sarvam.ai).
     ADR-005: LLM provider selection.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.infrastructure.interfaces import LLMPort


_SARVAM_LLM_BASE_URL = "https://api.sarvam.ai/v1"
_SARVAM_LLM_MODEL    = "sarvam-m"


class SarvamLLMClient(LLMPort):
    """
    Sarvam AI chat completions client.

    Environment Variables:
        SARVAM_API_KEY       — Sarvam AI subscription key (required)
        SARVAM_LLM_BASE_URL  — Override base URL (default: https://api.sarvam.ai/v1)
        SARVAM_LLM_MODEL     — Override model name (default: sarvam-m)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key  = api_key  or os.getenv("SARVAM_API_KEY",       "").strip()
        self.base_url = base_url or os.getenv("SARVAM_LLM_BASE_URL",  _SARVAM_LLM_BASE_URL).rstrip("/")
        self.model    = model    or os.getenv("SARVAM_LLM_MODEL",     _SARVAM_LLM_MODEL)

        if not self.api_key:
            raise ValueError(
                "Sarvam API key required. Set SARVAM_API_KEY environment variable."
            )

        from openai import OpenAI
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Call Sarvam chat completions with optional tool support.

        Returns OpenAI-compatible dict:
            {"content": "..."}  or  {"tool_calls": [...]}
        """
        openai_tools = []
        for tool in (tools or []):
            if "type" in tool:
                openai_tools.append(tool)
            else:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "parameters": tool.get("parameters", {}),
                    },
                })

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=openai_tools if openai_tools else None,
            tool_choice="auto" if openai_tools else None,
            temperature=0.3,
            max_tokens=256,
        )

        message = response.choices[0].message

        if message.tool_calls:
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }

        return {"content": message.content or ""}
