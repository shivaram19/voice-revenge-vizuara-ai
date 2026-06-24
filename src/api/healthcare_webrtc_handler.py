"""
Healthcare WebRTC Handler
=========================
Extends the base Moonshine WebRTC session with a HealthcareReceptionist.

Flow per session:
  1. Browser connects via /webrtc/offer with a ?phone= query param.
  2. Server looks up the patient by phone and starts the receptionist.
  3. Server sends a greeting message over the DataChannel.
  4. Browser microphone audio is transcribed by Moonshine.
  5. Each final transcript is forwarded to the receptionist.
  6. The receptionist's response is sent back as a DataChannel message.

For the MVP, agent responses are sent as text; the browser can render them
and optionally speak them via the Web Speech API. This keeps the MVP
runnable without cloud TTS credentials while preserving the full
conversation loop.

Ref: ADR-024; docs/engineering/goal-vector-healthcare-mvp.md.
"""

from __future__ import annotations

import asyncio
import json
import traceback
from typing import Any

from aiortc import RTCPeerConnection
from aiortc.rtcrtpreceiver import RemoteStreamTrack

from src.api.webrtc_handler import (
    MoonshineAudioTrack,
    WebRTCSession,
    _connections,
    _media_relay,
    logger,
)
from src.asr.moonshine_engine import MoonshineStreamingEngine
from src.receptionist.service import Receptionist


class HealthcareWebRTCSession(WebRTCSession):
    """
    WebRTC session with an injected HealthcareReceptionist.
    Overrides transcript handling to run the conversational agent loop.
    """

    def __init__(
        self,
        session_id: str,
        pc: RTCPeerConnection,
        engine: MoonshineStreamingEngine,
        receptionist: Receptionist,
        phone: str,
    ) -> None:
        super().__init__(session_id=session_id, pc=pc, engine=engine)
        self.receptionist = receptionist
        self.phone = phone
        self._greeting_sent = False

    @classmethod
    async def create(
        cls,
        session_id: str,
        engine: MoonshineStreamingEngine,
        receptionist: Receptionist,
        phone: str,
    ) -> HealthcareWebRTCSession:
        """Create a new healthcare WebRTC session."""
        pc = RTCPeerConnection()
        session = cls(
            session_id=session_id,
            pc=pc,
            engine=engine,
            receptionist=receptionist,
            phone=phone,
        )

        @pc.on("datachannel")
        def on_datachannel(channel: Any) -> None:
            session._data_channel = channel
            logger.info(
                "healthcare_datachannel_opened",
                session_id=session_id,
                label=channel.label,
            )

        @pc.on("track")
        def on_track(track: RemoteStreamTrack) -> None:
            if track.kind == "audio":
                asyncio.create_task(session._attach_audio(track))
            else:
                logger.info(
                    "healthcare_non_audio_track_ignored",
                    session_id=session_id,
                    kind=track.kind,
                )

        @pc.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            logger.info(
                "healthcare_connection_state_changed",
                session_id=session_id,
                state=pc.connectionState,
            )
            if pc.connectionState in ("failed", "closed", "disconnected"):
                await session.close()

        return session

    async def _attach_audio(self, track: RemoteStreamTrack) -> None:
        if self.moonshine_stream is None:
            self.moonshine_stream = await self.engine.create_stream(self.session_id)
        relayed = _media_relay.subscribe(track)
        self.audio_track = MoonshineAudioTrack(
            track=relayed,
            moonshine_stream=self.moonshine_stream,
        )
        self.audio_track.start()
        self._event_reader = asyncio.create_task(self._read_transcript_events())
        # Start the call once the audio track is attached.
        await self._start_call()

    async def _start_call(self) -> None:
        """Trigger the receptionist greeting and send it to the browser."""
        if self._greeting_sent:
            return
        self._greeting_sent = True
        try:
            greeting = await self.receptionist.handle_call_start(
                session_id=self.session_id,
                caller=self.phone,
                called="healthcare-mvp",
            )
            await self._send_agent_response(greeting, kind="greeting")
        except Exception as exc:
            logger.error(
                "healthcare_call_start_failed",
                session_id=self.session_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )

    async def _read_transcript_events(self) -> None:
        if self.moonshine_stream is None:
            return
        queue = self.moonshine_stream.events()
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                if self.pc.connectionState in ("failed", "closed", "disconnected"):
                    break
                continue
            except asyncio.CancelledError:
                break

            # Always forward transcript events so the browser can display them.
            await self._send_event(event)

            if event.is_final and event.text.strip():
                await self._handle_final_transcript(event.text)

    async def _handle_final_transcript(self, transcript: str) -> None:
        """Run the transcript through the receptionist and send the response."""
        try:
            response_text = await self.receptionist.handle_transcript(
                session_id=self.session_id,
                transcript=transcript,
            )
        except Exception as exc:
            logger.error(
                "healthcare_receptionist_error",
                session_id=self.session_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            response_text = "I am sorry, I did not catch that. Could you please repeat?"

        await self._send_agent_response(response_text, kind="response")

    async def _send_agent_response(self, text: str, kind: str = "response") -> None:
        if self._data_channel is None or self._data_channel.readyState != "open":
            logger.debug(
                "healthcare_datachannel_not_ready",
                session_id=self.session_id,
                kind=kind,
            )
            return
        try:
            self._data_channel.send(
                json.dumps({
                    "type": "agent_response",
                    "kind": kind,
                    "text": text,
                })
            )
        except Exception as exc:
            logger.warning(
                "healthcare_agent_response_send_failed",
                session_id=self.session_id,
                error=str(exc),
            )

    async def close(self) -> None:
        try:
            await self.receptionist.handle_call_end(self.session_id)
        except Exception as exc:
            logger.warning(
                "healthcare_call_end_failed",
                session_id=self.session_id,
                error=str(exc),
            )
        await super().close()


async def handle_healthcare_offer(
    engine: MoonshineStreamingEngine,
    receptionist_factory: Any,
    session_id: str,
    offer: dict[str, str],
    phone: str,
) -> dict[str, str]:
    """Create a new healthcare WebRTC session from a browser SDP offer."""
    if session_id in _connections:
        old_pc = _connections.pop(session_id)
        await old_pc.close()

    receptionist = receptionist_factory()
    session = await HealthcareWebRTCSession.create(
        session_id=session_id,
        engine=engine,
        receptionist=receptionist,
        phone=phone,
    )
    _connections[session_id] = session.pc
    answer = await session.create_answer(offer["sdp"], offer["type"])
    logger.info(
        "healthcare_answer_created",
        session_id=session_id,
        phone=phone,
        answer_type=answer["type"],
    )
    return answer
