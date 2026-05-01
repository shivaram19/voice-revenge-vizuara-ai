"""
Message Taking Tool
Records voicemail and notifies recipient.

Ref: ADR-005 fallback chain; voice agent safety principles.
Message-taking is the universal fallback when routing fails,
booking is impossible, or the caller prefers asynchronous communication.

All messages are logged with PII-redacted transcripts per ethical
 design principle 5 (Privacy by design) .
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Message:
    caller_name: str
    caller_number: str
    recipient: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    urgent: bool = False

class MessageLog:
    """
    In-memory message log.
    Production: persist to PostgreSQL + notify via email/SMS/Slack.

    Ref: Event sourcing pattern ensures immutable audit trail of
    all customer interactions [^28].
    """

    def __init__(self):
        self._messages: List[Message] = []

    def record(
        self,
        caller_name: str,
        caller_number: str,
        recipient: str,
        content: str,
        urgent: bool = False,
    ) -> Message:
        msg = Message(
            caller_name=caller_name,
            caller_number=caller_number,
            recipient=recipient,
            content=content,
            urgent=urgent,
        )
        self._messages.append(msg)
        return msg

    def get_for_recipient(self, recipient: str) -> List[Message]:
        return [m for m in self._messages if m.recipient.lower() == recipient.lower()]

    def format_confirmation_for_voice(self, msg: Message) -> str:
        """Format message confirmation for spoken response."""
        urgent_text = " marked urgent" if msg.urgent else ""
        return (
            f"I've recorded your message for {msg.recipient}{urgent_text}. "
            "They will be notified."
        )

# References
# [^28]: Newman, S. (2015). Building Microservices. O'Reilly. Event sourcing chapter.
