"""
Gateway WebSocket for Frontend Call Observability
Streams active call metadata and transcript events to dashboard clients.

Protocol:
    Client connects to /ws/gateway/calls
    Server sends initial snapshot of active calls
    Server pushes "transcript" events as they arrive
    Server sends "heartbeat" every 30s
    Client can disconnect anytime
"""

from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.infrastructure.call_state import CallStateManager
from src.api.gateway.models import WSMessage

router = APIRouter(tags=["gateway-websocket"])

_state = CallStateManager()
HEARTBEAT_INTERVAL = 30.0


@router.websocket("/ws/gateway/calls")
async def gateway_calls_websocket(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    await _state.subscribe(queue)

    # Send initial snapshot
    active = _state.get_active_calls()
    await websocket.send_json({
        "event": "snapshot",
        "payload": {
            "active_calls": [
                {
                    "call_sid": c.call_sid,
                    "student_name": c.student_name,
                    "parent_name": c.parent_name,
                    "call_type": c.call_type,
                    "duration_seconds": c.duration_seconds,
                    "status": c.status,
                    "transcript_count": len(c.transcripts),
                }
                for c in active
            ]
        }
    })

    # Start heartbeat + broadcast consumer
    heartbeat_task = asyncio.create_task(_heartbeat(websocket))
    consumer_task = asyncio.create_task(_consume_queue(websocket, queue))

    try:
        while True:
            # Keep connection alive; client can send ping or subscribe filters
            msg = await websocket.receive_text()
            # Minimal protocol: ignore client messages except for pings
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await _state.unsubscribe(queue)
        heartbeat_task.cancel()
        consumer_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


async def _heartbeat(websocket: WebSocket):
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await websocket.send_json({
                "event": "heartbeat",
                "payload": {"ts": asyncio.get_event_loop().time()}
            })
    except Exception:
        pass


async def _consume_queue(websocket: WebSocket, queue: asyncio.Queue):
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except Exception:
        pass
