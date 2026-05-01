"""
WebSocket Handler — Twilio Media Streams (Streaming Pipeline)
============================================================
Handles bidirectional audio relay between Twilio PSTN and the streaming
AI pipeline (Streaming STT → LLM → TTS).

Protocol (Twilio Media Streams):
    Inbound:
        "start"  → initialize CallSession + streaming pipeline + streamSid
        "media"  → stream μ-law 8 kHz audio chunks → pipeline
        "mark"   → playback tracking
        "stop"   → finalize session
    Outbound:
        "media"  → send synthesized μ-law 8 kHz audio back to caller

Critical Implementation Notes:
    1. Twilio requires `streamSid` in EVERY outbound media message [^43].
    2. Audio must be 8 kHz μ-law (G.711), matching the inbound format [^38].
    3. With streaming pipeline, TTS audio arrives asynchronously via callback.
       The pipeline pushes audio; the handler sends it [^22].
    4. Barge-in: pipeline detects user speech during AI speech and cancels
       the in-flight TTS task [^4][^OG1].
    5. Send loop yields control (asyncio.sleep) so task cancellation has
       an await point at which to take effect [^BI1][^PY1].
    6. Twilio Media Streams frames audio in 20 ms chunks (160 bytes at
       8 kHz μ-law) [^43]. Sending larger chunks causes buffering jitter.
    7. Twilio sends `media` events continuously; filtering `track != "inbound"`
       prevents echo-loop where the agent hears its own output [^44].

Research Provenance:
    - Twilio Media Streams relay 8 kHz μ-law over WebSocket [^43].
    - RFC 6455 WebSocket provides full-duplex, ordered messaging [^21].
    - ITU-T G.711 μ-law is the PSTN companding standard [^38].
    - Streaming architecture: audio pushed via async callback [^22].
    - Barge-in latency budget <300 ms; audio truncation <100 ms [^4].
    - Echo cancellation: agent output must not feed back into STT [^44].
    - asyncio event loop must yield between I/O bursts to remain responsive [^PY1].
"""

from __future__ import annotations

import json
import base64
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

from src.telephony.gateway import TelephonyGateway
from src.infrastructure.logging_config import (
    get_logger,
    set_call_start_time,
)
from src.infrastructure.telemetry import (
    get_tracer,
    log_call_start,
    log_call_end,
    log_exception,
    log_voice_event,
)
from src.infrastructure.call_state import CallStateManager
from src.api.gateway.db import GatewayDB, CallLog

logger = get_logger("api.websocket")
tracer = get_tracer()

# Twilio Media Streams chunk size: 8 kHz × 20 ms = 160 samples/bytes [^43][^38]
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
    call_start_time = asyncio.get_event_loop().time()
    turn_count = 0

    logger.info("websocket_connected", session_id=session_id)

    # Async callback: pipeline pushes audio here when TTS is ready [^22]
    async def send_audio(mulaw_bytes: bytes) -> None:
        if stream_sid is None:
            return
        await _send_audio(websocket, stream_sid, mulaw_bytes)

    with tracer.start_as_current_span("voice.call") as span:
        span.set_attribute("call.session_id", session_id)

        try:
            while True:
                message = await websocket.receive_text()
                event = json.loads(message)
                event_type = event.get("event")

                if event_type == "start":
                    # Anchor per-call wall clock for t_ms_since_call_start
                    # in every downstream log event (DFS-007 §6).
                    set_call_start_time(session_id)
                    start = event.get("start", {})
                    stream_sid = event.get("streamSid") or start.get("streamSid")
                    actual_call_sid = start.get("callSid", session_id)
                    metadata = gateway.parse_start_message(event)

                    custom_params = start.get("customParameters", {})
                    explicit_domain = custom_params.get("domain")
                    # `language` lets the outbound caller pre-seed the session
                    # language (e.g. "te-IN") so the greeting is synthesised in
                    # the right language without waiting for a transcript.
                    explicit_language = (custom_params.get("language") or "").strip()
                    # Twilio Media Streams does NOT include To/From for
                    # outbound calls in the `start` event — those live at
                    # the Voice API level. The outbound caller passes
                    # `parent_phone` as a <Parameter> in the TwiML so we
                    # can perform the verified-record lookup. Fall back
                    # to whatever the gateway parsed (inbound calls).
                    parent_phone_param = (custom_params.get("parent_phone") or "").strip()
                    effective_called = (
                        parent_phone_param
                        or metadata.to_number
                        or None
                    )

                    logger.info(
                        "media_stream_started",
                        session_id=session_id,
                        actual_call_sid=actual_call_sid,
                        stream_sid=stream_sid,
                        from_number=metadata.from_number,
                        to_number=metadata.to_number,
                        effective_called=effective_called,
                        domain=explicit_domain or "auto",
                        custom_params=custom_params,
                    )
                    log_call_start(
                        session_id,
                        metadata.from_number,
                        effective_called or "",
                        explicit_domain or "auto",
                    )

                    # Register with gateway for frontend observability
                    call_state = CallStateManager()
                    await call_state.register_call(
                        call_sid=actual_call_sid,
                        student_name=None,
                        parent_name=None,
                        parent_phone=effective_called,
                        call_type=explicit_domain or "inbound",
                        metadata={
                            "from_number": metadata.from_number,
                            "to_number": metadata.to_number,
                            "domain": explicit_domain or "auto",
                            "language": explicit_language,
                        },
                    )
                    # Persist call log
                    try:
                        gw_db = GatewayDB()
                        gw_db.create_call_log(CallLog(
                            id=None,
                            call_sid=actual_call_sid,
                            tenant_id="lincoln-high",
                            student_id=None,
                            domain=explicit_domain or "inbound",
                            direction="inbound",
                            phone_to=effective_called,
                            phone_from=metadata.from_number,
                            status="in-progress",
                            call_type=explicit_domain or "general",
                            duration_seconds=0,
                            transcript_summary=None,
                        ))
                    except Exception as db_err:
                        logger.warning("gateway_db_call_start_failed", error=str(db_err))

                    if pipeline:
                        await pipeline.on_call_start(
                            session_id,
                            metadata.from_number,
                            effective_called,
                            domain_id=explicit_domain,
                            send_callback=send_audio,
                            language=explicit_language,
                        )
                    else:
                        logger.warning("pipeline_unavailable", session_id=session_id)

                elif event_type == "media":
                    if not pipeline:
                        continue
                    # Twilio sends both "inbound" (caller) and "outbound" (agent)
                    # tracks. Filtering outbound prevents echo feedback [^44].
                    track = event.get("media", {}).get("track", "inbound")
                    if track != "inbound":
                        continue
                    payload_b64 = event["media"]["payload"]
                    await pipeline.on_media_chunk(session_id, payload_b64)

                elif event_type == "mark":
                    mark_name = event["mark"]["name"]
                    logger.info("mark_received", session_id=session_id, mark=mark_name)

                elif event_type == "stop":
                    duration = asyncio.get_event_loop().time() - call_start_time
                    logger.info("call_stopped", session_id=session_id, duration_sec=round(duration, 1))
                    if pipeline:
                        summary = await pipeline.on_call_end(session_id)
                        if summary:
                            turn_count = len(summary.conversation_history)
                            logger.info(
                                "session_summary",
                                session_id=session_id,
                                turns=turn_count,
                            )
                    log_call_end(session_id, turn_count, duration)

                    # Finalize gateway call state
                    try:
                        call_state = CallStateManager()
                        finalized = await call_state.finalize_call(session_id, status="completed")
                        if finalized:
                            gw_db = GatewayDB()
                            gw_db.update_call_log(session_id, {
                                "status": "completed",
                                "duration_seconds": finalized.duration_seconds,
                                "ended_at": finalized.ended_at.isoformat() if finalized.ended_at else None,
                            })
                    except Exception as gw_err:
                        logger.warning("gateway_finalize_failed", error=str(gw_err))
                    break

        except WebSocketDisconnect:
            logger.info("websocket_disconnected", session_id=session_id)
        except Exception as e:
            logger.error("websocket_error", session_id=session_id, error=str(e), exc_info=True)
            log_exception(e, session_id, {"handler": "websocket"})
        finally:
            if pipeline:
                await pipeline.on_call_end(session_id)
            logger.info("session_finalized", session_id=session_id)


async def _send_audio(
    websocket: WebSocket,
    stream_sid: str,
    mulaw_bytes: bytes,
) -> None:
    """
    Send μ-law audio back to Twilio as a media event.
    Chunks into ~20 ms frames (160 bytes) to match telephony framing [^43][^16].
    Yields control between chunks so barge-in cancellation can take effect [^BI1][^PY1].
    """
    for i in range(0, len(mulaw_bytes), _TWILIO_CHUNK_BYTES):
        chunk = mulaw_bytes[i : i + _TWILIO_CHUNK_BYTES]
        payload = base64.b64encode(chunk).decode("ascii")
        msg = {
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload},
        }
        await websocket.send_text(json.dumps(msg))
        # Yield control — gives the event loop a chance to process
        # barge-in cancellation before queuing the next chunk [^BI1][^PY1]
        await asyncio.sleep(0)


# References
# [^4]: Deepgram / ElevenLabs. (2026). Barge-In & Turn-Taking Guide.
# [^16]: Twilio. Media Streams framing. 20 ms chunks at 8 kHz.
# [^21]: Fette, I., & Melnikov, A. (2011). RFC 6455: The WebSocket Protocol. IETF.
# [^22]: Gladia. (2025). Concurrent pipelines for voice AI.
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation.
# [^43]: Twilio. (2024). Media Streams API Documentation.
# [^44]: Sondhi, M. M. (1967). An Adaptive Echo Canceller. Bell System Technical
#         Journal, 46(3), 497–511.  Echo cancellation prevents feedback loops.
# [^BI1]: Hamming AI. (2026). Barge-in recovery: yield between audio chunks.
# [^OG1]: Orga AI. (2026). Barge-in for Voice Agents. orga-ai.com/blog/blog-barge-in-voice-agents-guide
# [^PY1]: Python asyncio docs. (2024). Executing code in thread or process pools.
#          docs.python.org/3/library/asyncio-eventloop.html#executing-code-in-thread-or-process-pools
