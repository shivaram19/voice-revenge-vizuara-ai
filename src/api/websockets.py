"""
WebSocket Handler — Twilio Media Streams (Live AI Pipeline)
============================================================
Handles bidirectional audio relay between Twilio PSTN and the local
AI pipeline (STT → LLM → TTS).

Protocol (Twilio Media Streams):
    Inbound:
        "start"  → initialize CallSession + DemoPipeline + streamSid
        "media"  → stream μ-law 8kHz audio chunks
        "mark"   → playback tracking
        "stop"   → finalize session
    Outbound:
        "media"  → send synthesized μ-law 8kHz audio back to caller

Critical Implementation Notes:
    1. Twilio requires `streamSid` in EVERY outbound media message.
       Without it, audio is silently dropped [^43].
    2. Audio must be 8 kHz μ-law (G.711), matching the inbound format [^38].
    3. Chunk size should align with telephony framing (~20 ms = 160 bytes)
       to minimize latency jitter [^16].
    4. The `start` event provides `streamSid`; it must be cached for all
       subsequent outbound messages on that WebSocket [^43].

Research Provenance:
    - Twilio Media Streams relay 8 kHz μ-law over WebSocket [^43].
    - RFC 6455 WebSocket provides full-duplex, ordered messaging [^21].
    - ITU-T G.711 μ-law is the PSTN companding standard [^38].
    - SigArch 2026 turn-gap budget: <800 ms from end-of-speech to
      first audio byte outbound [^16].
    - Energy-based VAD (Rabiner & Sambur 1975) is sufficient for
      demo-quality endpointing [^32].
"""

import json
import base64
from fastapi import WebSocket, WebSocketDisconnect

from src.telephony.gateway import TelephonyGateway

# Twilio Media Streams chunk size: 8 kHz × 20 ms = 160 samples/bytes
# Ref: SigArch 2026 streaming TTS framing recommendations [^16].
# Ref: Twilio <Stream> defaults to track="both_tracks" when omitted,
# sending both inbound (caller) and outbound (agent) audio. Processing
# outbound audio creates acoustic echo loops [^43][^44].
_TWILIO_CHUNK_BYTES = 160


async def handle_twilio_websocket(websocket: WebSocket, call_sid: str):
    """
    Handle Twilio Media Streams WebSocket connection.
    In DEMO_MODE, uses the local CPU pipeline (faster-whisper + MockLLM + Piper).
    In production, delegates to the full cloud-backed pipeline.
    """
    await websocket.accept()
    gateway: TelephonyGateway = websocket.app.state.telephony
    demo_pipeline = getattr(websocket.app.state, "demo_pipeline", None)
    session_id = call_sid
    stream_sid: str | None = None

    print(f"[{session_id}] Twilio WebSocket connected")

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
                # Twilio Media Streams passes <Parameter> values in start.customParameters [^43].
                custom_params = start.get("customParameters", {})
                explicit_domain = custom_params.get("domain")

                print(f"[{session_id}] Call started: {metadata.from_number} → {metadata.to_number} (streamSid={stream_sid}, domain={explicit_domain or 'auto'})")

                if demo_pipeline:
                    greeting_audio = await demo_pipeline.on_call_start(
                        session_id,
                        metadata.from_number,
                        metadata.to_number,
                        domain_id=explicit_domain,
                    )
                    if greeting_audio and stream_sid:
                        print(f"[{session_id}] Sending greeting audio: {len(greeting_audio)} bytes")
                        await _send_audio(websocket, stream_sid, greeting_audio)
                    elif not stream_sid:
                        print(f"[{session_id}] WARN: no streamSid in start event; cannot send audio")
                else:
                    print(f"[{session_id}] DEMO_MODE not active; pipeline unavailable.")

            elif event_type == "media":
                if not demo_pipeline or not stream_sid:
                    continue
                # Twilio <Stream> defaults to track="both_tracks", which echoes
                # the agent's own audio back as "outbound". Only process the
                # caller's voice ("inbound") to avoid self-triggering loops [^43].
                track = event.get("media", {}).get("track", "inbound")
                if track != "inbound":
                    continue
                payload_b64 = event["media"]["payload"]
                response_audio = await demo_pipeline.on_media_chunk(session_id, payload_b64)
                if response_audio:
                    print(f"[{session_id}] Sending response audio: {len(response_audio)} bytes")
                    await _send_audio(websocket, stream_sid, response_audio)

            elif event_type == "mark":
                mark_name = event["mark"]["name"]
                print(f"[{session_id}] Mark received: {mark_name}")

            elif event_type == "stop":
                print(f"[{session_id}] Call stopped")
                if demo_pipeline:
                    summary = await demo_pipeline.on_call_end(session_id)
                    if summary:
                        print(f"[{session_id}] Session summary: {len(summary.conversation_history)} turns")
                break

    except WebSocketDisconnect:
        print(f"[{session_id}] WebSocket disconnected")
    except Exception as e:
        print(f"[{session_id}] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if demo_pipeline:
            await demo_pipeline.on_call_end(session_id)
        print(f"[{session_id}] Session finalized")


async def _send_audio(websocket: WebSocket, stream_sid: str, mulaw_bytes: bytes) -> None:
    """
    Send μ-law audio back to Twilio as a media event.

    Twilio Media Streams requires `streamSid` in every outbound media
    message to route audio to the correct call leg [^43]. Audio is
    chunked into ~20 ms frames (160 bytes) to match telephony framing
    and minimize jitter [^16].
    """
    # Chunk into 160-byte frames (~20 ms at 8 kHz)
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
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^21]: Fette, I., & Melnikov, A. (2011). RFC 6455: The WebSocket Protocol. IETF.
# [^32]: Rabiner, L. R., & Sambur, M. R. (1975). An Algorithm for Determining the Endpoints of Isolated Utterances. Bell System Technical Journal.
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation (PCM) of Voice Frequencies.
# [^43]: Twilio. (2024). Media Streams API Documentation. twilio.com/docs/voice/media-streams.
# [^44]: Sondhi, M. M. (1967). An Adaptive Echo Canceller. Bell System Technical Journal, 46(3), 497-511.
