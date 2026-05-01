"""
Call State Manager
In-memory singleton for tracking active voice calls and their transcripts.
Used by the frontend gateway WebSocket to stream real-time call observability.

Design:
    - asyncio.Lock for structural mutations (register/deregister calls)
    - Lock-free list append for transcripts (per-call list reference is stable)
    - O(1) lookup by call_sid via dict

Refs:
    - asyncio synchronization primitives (Python docs)
    - Observer pattern (Gamma et al. 1994)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class TranscriptLine:
    speaker: str  # "agent" | "user"
    text: str
    timestamp_ms: int
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ActiveCall:
    call_sid: str
    student_name: Optional[str]
    parent_name: Optional[str]
    parent_phone: Optional[str]
    call_type: str  # e.g. "Absence Verification", "Fee Reminder"
    status: str  # "in-progress", "completed", "failed"
    duration_seconds: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    transcripts: List[TranscriptLine] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CallStateManager:
    """
    Singleton managing active call state for real-time observability.
    Thread-safe via asyncio.Lock.
    """

    _instance: Optional["CallStateManager"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> "CallStateManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._calls: Dict[str, ActiveCall] = {}
            cls._instance._observers: List[asyncio.Queue] = []
            cls._instance._structural_lock = asyncio.Lock()
        return cls._instance

    # ------------------------------------------------------------------
    # Call lifecycle
    # ------------------------------------------------------------------

    async def register_call(
        self,
        call_sid: str,
        student_name: Optional[str] = None,
        parent_name: Optional[str] = None,
        parent_phone: Optional[str] = None,
        call_type: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActiveCall:
        async with self._structural_lock:
            call = ActiveCall(
                call_sid=call_sid,
                student_name=student_name,
                parent_name=parent_name,
                parent_phone=parent_phone,
                call_type=call_type,
                status="in-progress",
                metadata=metadata or {},
            )
            self._calls[call_sid] = call
            return call

    async def finalize_call(self, call_sid: str, status: str = "completed") -> Optional[ActiveCall]:
        async with self._structural_lock:
            call = self._calls.get(call_sid)
            if call is None:
                return None
            call.status = status
            call.ended_at = datetime.utcnow()
            call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())
            # Keep in memory for a short window, but mark as ended
            return call

    async def deregister_call(self, call_sid: str) -> None:
        async with self._structural_lock:
            self._calls.pop(call_sid, None)

    # ------------------------------------------------------------------
    # Transcripts
    # ------------------------------------------------------------------

    async def append_transcript(
        self, call_sid: str, speaker: str, text: str, timestamp_ms: int = 0
    ) -> None:
        """
        Append a transcript line. Lock-free because per-call list is stable.
        """
        call = self._calls.get(call_sid)
        if call is None:
            return
        line = TranscriptLine(speaker=speaker, text=text, timestamp_ms=timestamp_ms)
        call.transcripts.append(line)
        await self._broadcast({
            "event": "transcript",
            "call_sid": call_sid,
            "speaker": speaker,
            "text": text,
            "timestamp_ms": timestamp_ms,
        })

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_calls(self) -> List[ActiveCall]:
        return [
            call for call in self._calls.values()
            if call.status == "in-progress"
        ]

    def get_call(self, call_sid: str) -> Optional[ActiveCall]:
        return self._calls.get(call_sid)

    def get_all_calls(self) -> List[ActiveCall]:
        return list(self._calls.values())

    # ------------------------------------------------------------------
    # Observer pattern (WebSocket broadcast)
    # ------------------------------------------------------------------

    async def subscribe(self, queue: asyncio.Queue) -> None:
        async with self._structural_lock:
            self._observers.append(queue)

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        async with self._structural_lock:
            if queue in self._observers:
                self._observers.remove(queue)

    async def _broadcast(self, message: Dict[str, Any]) -> None:
        dead: List[asyncio.Queue] = []
        for q in self._observers:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                dead.append(q)
        if dead:
            async with self._structural_lock:
                for q in dead:
                    if q in self._observers:
                        self._observers.remove(q)
