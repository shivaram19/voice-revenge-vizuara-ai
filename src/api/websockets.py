"""
WebSocket Handler — Twilio Media Streams
SRP: ONLY WebSocket protocol handling. Delegates to domain layer.
Ref: Twilio (2024). Media Streams API [^43]; SigArch 2026 [^16].
"""

import json
from fastapi import WebSocket, WebSocketDisconnect

from src.telephony.gateway import TelephonyGateway


async def handle_twilio_websocket(websocket: WebSocket, call_sid: str):
    """
    Handle Twilio Media Streams WebSocket connection.

    Protocol:
    1. "start" event → initialize CallSession
    2. "media" events → stream audio to STT → LLM → TTS
    3. "mark" events → track playback completion
    4. "stop" event → finalize session
    """
    await websocket.accept()
    gateway: TelephonyGateway = websocket.app.state.telephony
    session_id = call_sid

    print(f"[{session_id}] Twilio WebSocket connected")

    try:
        while True:
            message = await websocket.receive_text()
            event = json.loads(message)
            event_type = event.get("event")

            if event_type == "start":
                metadata = gateway.parse_start_message(event)
                print(f"[{session_id}] Call started: {metadata}")
                # TODO: Initialize ConstructionReceptionist session

            elif event_type == "media":
                payload = event["media"]["payload"]
                pcm = gateway.decode_inbound(payload.encode())
                # TODO: Stream to STT, run pipeline through ConstructionReceptionist

            elif event_type == "mark":
                mark_name = event["mark"]["name"]
                print(f"[{session_id}] Mark received: {mark_name}")

            elif event_type == "stop":
                print(f"[{session_id}] Call stopped")
                break

    except WebSocketDisconnect:
        print(f"[{session_id}] WebSocket disconnected")
    except Exception as e:
        print(f"[{session_id}] Error: {e}")
    finally:
        # TODO: Finalize CallSession
        print(f"[{session_id}] Session finalized")


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
# [^43]: Twilio. (2024). Media Streams API Documentation.
