"""
Conversation Module
Voice interaction with human respect.

Exports:
    TurnTakingEngine    — Floor management, barge-in detection
    AttentivenessEngine — Emotional intelligence, response timing
    ConversationCoordinator — Full pipeline orchestration
"""

from src.conversation.turn_taking import TurnTakingEngine, TurnTakingConfig, TurnState, UserReadiness
from src.conversation.attentiveness import AttentivenessEngine, AttentivenessConfig, AttentionState, EmotionalTone
from src.conversation.coordinator import ConversationCoordinator, CoordinatorConfig

__all__ = [
    "TurnTakingEngine",
    "TurnTakingConfig",
    "TurnState",
    "UserReadiness",
    "AttentivenessEngine",
    "AttentivenessConfig",
    "AttentionState",
    "EmotionalTone",
    "ConversationCoordinator",
    "CoordinatorConfig",
]
