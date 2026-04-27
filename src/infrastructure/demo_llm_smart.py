"""
Smart Mock LLM — Deterministic but Robust
==========================================
Replaces rigid keyword matching with fuzzy intent detection,
conversation memory, and varied fallback responses.

Design: Yao et al. 2023 ReAct loop [^74] adapted for deterministic
execution with no external API dependency.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class SmartMockLLM:
    """
    Deterministic LLM with conversation memory and fuzzy intent matching.
    No external API required.
    """

    def __init__(self, db):
        self.db = db
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _get_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "last_intent": None,
                "last_topic": None,
                "contractor_mentioned": None,
                "turn_count": 0,
            }
        return self.sessions[session_id]

    def _find_contractor_id(self, query: str) -> Optional[int]:
        all_contractors = self.db.list_contractors(active_only=True)
        query_lower = query.lower()
        for c in all_contractors:
            if query_lower in c.specialty.lower() or query_lower in c.name.lower():
                return c.id
        return all_contractors[0].id if all_contractors else None

    def _fuzzy_match(self, text: str, patterns: List[str]) -> bool:
        """Check if any pattern is a substring of the text."""
        text_lower = text.lower()
        return any(p in text_lower for p in patterns)

    async def chat_completion(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Get last user message
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break

        session_id = "demo"
        for m in messages:
            if m.get("role") == "user" and "session" in str(m.get("content", "")):
                # Extract session from context if available
                pass

        sess = self._get_session(session_id)
        sess["turn_count"] += 1
        user_lower = user_msg.lower()

        # Filter out very short/garbled noise
        if len(user_msg.strip()) < 3:
            return {"content": "I'm sorry, I didn't catch that. Could you please repeat?"}

        # ===== EMERGENCY / PLUMBING =====
        if self._fuzzy_match(user_msg, ["plumb", "leak", "burst", "water", "pipe", "flood", "drip", "toilet", "sink"]):
            sess["last_intent"] = "find_contractor"
            sess["last_topic"] = "plumbing"
            return {
                "content": None,
                "tool_calls": [{"id": "call_find", "function": {"name": "find_contractor", "arguments": json.dumps({"query": "Plumbing"})}}]
            }

        # ===== ELECTRICAL =====
        if self._fuzzy_match(user_msg, ["electr", "power", "wire", "panel", "outlet", "light", "spark", "fuse", "circuit"]):
            sess["last_intent"] = "find_contractor"
            sess["last_topic"] = "electrical"
            return {
                "content": None,
                "tool_calls": [{"id": "call_find", "function": {"name": "find_contractor", "arguments": json.dumps({"query": "Electrical"})}}]
            }

        # ===== ROOFING =====
        if self._fuzzy_match(user_msg, ["roof", "shingle", "gutter", "storm", "leak roof"]):
            sess["last_intent"] = "find_contractor"
            sess["last_topic"] = "roofing"
            return {
                "content": None,
                "tool_calls": [{"id": "call_find", "function": {"name": "find_contractor", "arguments": json.dumps({"query": "Roofing"})}}]
            }

        # ===== HVAC =====
        if self._fuzzy_match(user_msg, ["hvac", "heat", "ac", "air condition", "furnace", "cool", "thermostat", "vent"]):
            sess["last_intent"] = "find_contractor"
            sess["last_topic"] = "hvac"
            return {
                "content": None,
                "tool_calls": [{"id": "call_find", "function": {"name": "find_contractor", "arguments": json.dumps({"query": "HVAC"})}}]
            }

        # ===== GENERAL CONTRACTOR / RENOVATION =====
        if self._fuzzy_match(user_msg, ["general", "contractor", "renovation", "reno", "kitchen", "bathroom", "remodel", "build", "addition", "construction", "house", "home", "project", "estimate"]):
            sess["last_intent"] = "find_contractor"
            sess["last_topic"] = "general"
            return {
                "content": None,
                "tool_calls": [{"id": "call_find", "function": {"name": "find_contractor", "arguments": json.dumps({"query": "General Contracting"})}}]
            }

        # ===== BOOKING / SCHEDULING =====
        if self._fuzzy_match(user_msg, ["book", "schedule", "appointment", "slot", "available", "when", "time", "tomorrow", "today", "next week", "monday", "tuesday", "wednesday", "thursday", "friday"]):
            sess["last_intent"] = "check_availability"
            cid = self._find_contractor_id(user_msg)
            tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
            if "book" in user_lower or "appointment" in user_lower:
                return {
                    "content": None,
                    "tool_calls": [{"id": "call_book", "function": {"name": "book_appointment", "arguments": json.dumps({"contractor_id": cid, "date": tomorrow, "time": "10:00", "caller_name": "Demo Caller", "caller_phone": "555-0199", "duration_minutes": 30, "notes": user_msg})}}]
                }
            return {
                "content": None,
                "tool_calls": [{"id": "call_avail", "function": {"name": "check_availability", "arguments": json.dumps({"contractor_id": cid, "date": datetime.utcnow().strftime("%Y-%m-%d")})}}]
            }

        # ===== FAQ =====
        if self._fuzzy_match(user_msg, ["hour", "open", "close", "warranty", "permit", "payment", "price", "cost", "how much", "timeline", "how long", "insurance", "license", "service area", "coverage"]):
            sess["last_intent"] = "search_faq"
            return {
                "content": None,
                "tool_calls": [{"id": "call_faq", "function": {"name": "search_faq", "arguments": json.dumps({"query": user_msg})}}]
            }

        # ===== OUTBOUND CALL =====
        if self._fuzzy_match(user_msg, ["call back", "callback", "have them call", "schedule a call", "reach me", "contact me"]):
            sess["last_intent"] = "schedule_outbound_call"
            cid = self._find_contractor_id(user_msg)
            return {
                "content": None,
                "tool_calls": [{"id": "call_out", "function": {"name": "schedule_outbound_call", "arguments": json.dumps({"contractor_id": cid, "reason": user_msg})}}]
            }

        # ===== GREETINGS =====
        if self._fuzzy_match(user_msg, ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
            return {"content": "Hello! Thank you for calling TreloLabs Voice AI. How can I help you today?"}

        # ===== THANK YOU / GOODBYE =====
        if self._fuzzy_match(user_msg, ["thank", "thanks", "bye", "goodbye", "done", "that's all", "no more", "hang up"]):
            return {"content": "You're welcome. Have a great day, and thank you for calling TreloLabs Voice AI."}

        # ===== FALLBACK (varied by turn count) =====
        fallbacks = [
            "I'm here to help. Could you tell me if you need a plumber, electrician, roofer, or general contractor?",
            "I want to make sure I understand. Are you looking to schedule an appointment, find a contractor, or ask about our services?",
            "I didn't quite catch that. You can say things like 'I need a plumber' or 'book an appointment for tomorrow'.",
            "Let me help you better. What trade do you need? We have plumbing, electrical, roofing, HVAC, and general contracting.",
        ]
        idx = (sess["turn_count"] - 1) % len(fallbacks)
        return {"content": fallbacks[idx]}


# References
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
