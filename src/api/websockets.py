"""
WebSocket Handler — Twilio Media Streams (Streaming Pipeline)
============================================================
Handles bidirectional audio relay between Twilio PSTN and the streaming
AI pipeline (Streaming STT → LLM → TTS).

Protocol (Twilio Media Streams):
    Inbound:
        "start"  → initialize CallSession + streaming pipeline + streamSid
        "media"  → stream μ-law 8kHz audio chunks → pipeline
        "mark"   → playback tracking
        "stop"   → finalize session
    Outbound:
        "media"  → send synthesized μ-law 8kHz audio back to caller

Critical Implementation Notes:
    1. Twilio requires `streamSid` in EVERY outbound media message [^43].
    2. Audio must be 8 kHz μ-law (G.711), matching the inbound format [^38].
    3. With streaming pipeline, TTS audio arrives asynchronously via callback.
       The pipeline pushes audio; the handler sends it [^22].
    4. Barge-in: pipeline detects user speech during AI speech and cancels
       the in-flight TTS task [^4][^5].

Research Provenance:
    - Twilio Media Streams relay 8 kHz μ-law over WebSocket [^43].
    - RFC 6455 WebSocket provides full-duplex, ordered messaging [^21].
    - ITU-T G.711 μ-law is the PSTN companding standard [^38].
    - Streaming architecture: audio pushed via async callback [^22].
"""

import json
import base64
from fastapi import WebSocket, WebSocketDisconnect

from src.telephony.gateway import TelephonyGateway

# Twilio Media Streams chunk size: 8 kHz × 20 ms = 160 samples/bytes
_TWILIO_CHUNK_BYTES = 160


async def handle_twilio_websocket(websocket: WebSocket, call_sid: str):
    """
    Handle Twilio Media Streams WebSocket connection.
    Uses the streaming pipeline: audio flows in, responses flow out via callback.
    """
    await websocket.accept()
    gateway: TelephonyGateway = websocket.app.state.telephony
    pipeline = getattr(websocket.app.state, "demo_pipeline", None)
    session_id = call_sid
    stream_sid: str | None = None

    print(f"[{session_id}] Twilio WebSocket connected")

    # Async callback: pipeline pushes audio here when TTS is ready
    async def send_audio(mulaw_bytes: bytes) -> None:
        if stream_sid is None:
            return
        await _send_audio(websocket, stream_sid, mulaw_bytes)

    try:
        while True:
            message = await websocket.receive_text()
            event = json.loads(message)
            event_type = event.get("event")

            if event_type == "start":
                start = event.get("start", {})
                stream_sid = event.get("streamSid") or start.get("streamSid")
                metadata = gateway.parse_start_message(event)

                # Extract explicit domain from custom parameters (outbound calls).
                custom_params = start.get("customParameters", {})
                explicit_domain = custom_params.get("domain")

                print(
                    f"[{session_id}] Call started: {metadata.from_number} → "
                    f"{metadata.to_number} (streamSid={stream_sid}, "
                    f"domain={explicit_domain or 'auto'})"
                )

                if pipeline:
                    await pipeline.on_call_start(
                        session_id,
                        metadata.from_number,
                        metadata.to_number,
                        domain_id=explicit_domain,
                        send_callback=send_audio,
                    )
                else:
                    print(f"[{session_id}] WARN: pipeline unavailable")

            elif event_type == "media":
                if not pipeline:
                    continue
                # Only process caller's voice ("inbound") to avoid echo loops [^43]
                track = event.get("media", {}).get("track", "inbound")
                if track != "inbound":
                    continue
                payload_b64 = event["media"]["payload"]
                await pipeline.on_media_chunk(session_id, payload_b64)

            elif event_type == "mark":
                mark_name = event["mark"]["name"]
                print(f"[{session_id}] Mark received: {mark_name}")

            elif event_type == "stop":
                print(f"[{session_id}] Call stopped")
                if pipeline:
                    summary = await pipeline.on_call_end(session_id)
                    if summary:
                        print(
                            f"[{session_id}] Session summary: "
                            f"{len(summary.conversation_history)} turns"
                        )
                break

    except WebSocketDisconnect:
        print(f"[{session_id}] WebSocket disconnected")
    except Exception as e:
        print(f"[{session_id}] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if pipeline:
            await pipeline.on_call_end(session_id)
        print(f"[{session_id}] Session finalized")


async def _send_audio(websocket: WebSocket, stream_sid: str, mulaw_bytes: bytes) -> None:
    """
    Send μ-law audio back to Twilio as a media event.
    Chunks into ~20 ms frames (160 bytes) to match telephony framing [^16].
    """
    for i in range(0, len(mulaw_bytes), _TWILIO_CHUNK_BYTES):
        chunk = mulaw_bytes[i:i + _TWILIO_CHUNK_BYTES]
        payload = base64.b64encode(chunk).decode("ascii")
        msg = {
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload},
        }
        await websocket.send_text(json.dumps(msg))


# References
# [^4]: Deepgram / ElevenLabs. (2026). Barge-In & Turn-Taking Guide.
# [^5]: LiveKit. (2026). Adaptive Interruption Handling.
# [^21]: Fette, I., & Melnikov, A. (2011). RFC 6455: The WebSocket Protocol. IETF.
# [^22]: Gladia. (2025). Concurrent pipelines for voice AI.
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation.
# [^43]: Twilio. (2024). Media Streams API Documentation.
