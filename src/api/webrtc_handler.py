"""
WebRTC Handler for Browser-to-Server Real-Time ASR
==================================================
Accepts an audio track from a browser via aiortc, resamples incoming PCM
frames to 16 kHz mono, and feeds them into the Moonshine v2 streaming engine.
Transcript events are pushed back to the browser over the same peer
connection's RTCDataChannel.

Research Provenance:
    - WebRTC is the de-facto standard for sub-100ms browser media transport;
      aiortc implements the Python server-side stack (RFC 8829) [^aiortc].
    - Moonshine v2 streaming achieves ~200 ms first-word latency on Linux
      with native streaming inference [^Moonshine2026].
    - Resampling to 16 kHz before ASR is standard; scipy.signal.resample_poly
      provides efficient polyphase resampling [^scipy].

Ref: ADR-024 (WebRTC Transport for Self-Hosted ASR)
"""

from __future__ import annotations

import asyncio
import json
import time
import traceback
from typing import Any, Dict, Optional

import av
import numpy as np
import scipy.signal
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
from aiortc.rtcrtpreceiver import RemoteStreamTrack

from src.asr.moonshine_engine import (
    MoonshineStreamingEngine,
    MoonshineStream,
    MoonshineTranscriptEvent,
)
from src.infrastructure.logging_config import get_logger

logger = get_logger("api.webrtc")

# Global media relay so that multiple consumers can safely subscribe to the
# same browser track without re-encoding.
_media_relay = MediaRelay()

# In-memory registry of active peer connections, keyed by session id.
# Production deployments should pair this with Redis or sticky routing.
_connections: Dict[str, RTCPeerConnection] = {}


class MoonshineAudioTrack:
    """
    Consumes a remote audio track, resamples frames to 16 kHz mono float32,
    and forwards them to a Moonshine stream.
    """

    def __init__(
        self,
        track: RemoteStreamTrack,
        moonshine_stream: MoonshineStream,
        target_sample_rate: int = 16000,
    ) -> None:
        self.track = track
        self.moonshine_stream = moonshine_stream
        self.target_sample_rate = target_sample_rate
        self._task: Optional[asyncio.Task] = None
        self._closed = False
        self._residual_buffer: np.ndarray = np.array([], dtype=np.float32)
        self._frames_received = 0
        self._frames_dropped = 0

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())
            self._task.add_done_callback(self._on_done)

    def _on_done(self, task: asyncio.Task) -> None:
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            logger.error(
                "webrtc_track_task_failed",
                session_id=self.moonshine_stream.session_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )

    async def _run(self) -> None:
        logger.info(
            "webrtc_track_started",
            session_id=self.moonshine_stream.session_id,
            target_sample_rate=self.target_sample_rate,
        )
        try:
            while not self._closed:
                try:
                    frame: av.audio.frame.AudioFrame = await self.track.recv()
                except Exception as exc:
                    logger.warning(
                        "webrtc_track_recv_error",
                        session_id=self.moonshine_stream.session_id,
                        error=str(exc),
                    )
                    break

                await self._process_frame(frame)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "webrtc_track_error",
                session_id=self.moonshine_stream.session_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
        finally:
            logger.info(
                "webrtc_track_stopped",
                session_id=self.moonshine_stream.session_id,
                frames_received=self._frames_received,
                frames_dropped=self._frames_dropped,
            )

    async def _process_frame(self, frame: av.audio.frame.AudioFrame) -> None:
        self._frames_received += 1

        # Convert PyAV frame to numpy. shape is (channels, samples).
        try:
            ndarray = frame.to_ndarray()
        except Exception as exc:
            logger.warning(
                "webrtc_frame_decode_failed",
                session_id=self.moonshine_stream.session_id,
                error=str(exc),
            )
            self._frames_dropped += 1
            return

        # Convert integer PCM to float32 in [-1.0, 1.0].
        if ndarray.dtype != np.float32:
            max_val = np.iinfo(ndarray.dtype).max
            ndarray = ndarray.astype(np.float32) / max_val
        else:
            ndarray = ndarray.astype(np.float32, copy=False)

        # av AudioFrame arrays are (channels, samples). Moonshine expects mono.
        if ndarray.ndim == 1:
            mono = ndarray
        else:
            mono = ndarray.mean(axis=0)

        # Resample to target sample rate. scipy is already a project dependency
        # and avoids pulling in resampy (librosa's optional resampler).
        if frame.sample_rate != self.target_sample_rate:
            gcd = np.gcd(int(frame.sample_rate), int(self.target_sample_rate))
            up = self.target_sample_rate // gcd
            down = frame.sample_rate // gcd
            mono = scipy.signal.resample_poly(mono, up, down)
            mono = mono.astype(np.float32, copy=False)

        # Accumulate residual so we feed Moonshine reasonably sized chunks.
        # 0.5-second chunks keep latency low without excessive thread context
        # switches for every 20 ms RTP frame.
        self._residual_buffer = np.concatenate([self._residual_buffer, mono])
        chunk_samples = int(self.target_sample_rate * 0.5)

        while len(self._residual_buffer) >= chunk_samples:
            chunk = self._residual_buffer[:chunk_samples]
            self._residual_buffer = self._residual_buffer[chunk_samples:]
            await self.moonshine_stream.add_audio(chunk, self.target_sample_rate)

    async def close(self) -> None:
        self._closed = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


class WebRTCSession:
    """
    Manages one browser-to-server WebRTC session:
      - RTCPeerConnection lifecycle
      - audio track ingestion
      - Moonshine ASR stream
      - DataChannel transcript forwarding
    """

    def __init__(
        self,
        session_id: str,
        pc: RTCPeerConnection,
        engine: MoonshineStreamingEngine,
    ) -> None:
        self.session_id = session_id
        self.pc = pc
        self.engine = engine
        self.moonshine_stream: Optional[MoonshineStream] = None
        self.audio_track: Optional[MoonshineAudioTrack] = None
        self._data_channel: Optional[Any] = None
        self._event_reader: Optional[asyncio.Task] = None
        self._start_time = time.time()

    @classmethod
    async def create(
        cls,
        session_id: str,
        engine: MoonshineStreamingEngine,
    ) -> "WebRTCSession":
        pc = RTCPeerConnection()
        session = cls(session_id=session_id, pc=pc, engine=engine)

        @pc.on("datachannel")
        def on_datachannel(channel: Any) -> None:
            session._data_channel = channel
            logger.info(
                "webrtc_datachannel_opened",
                session_id=session_id,
                label=channel.label,
            )

        @pc.on("track")
        def on_track(track: RemoteStreamTrack) -> None:
            if track.kind == "audio":
                asyncio.create_task(session._attach_audio(track))
            else:
                logger.info(
                    "webrtc_non_audio_track_ignored",
                    session_id=session_id,
                    kind=track.kind,
                )

        @pc.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            logger.info(
                "webrtc_connection_state_changed",
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

    async def _read_transcript_events(self) -> None:
        if self.moonshine_stream is None:
            return
        queue = self.moonshine_stream.events()
        while True:
            try:
                event: MoonshineTranscriptEvent = await asyncio.wait_for(
                    queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                if self.pc.connectionState in ("failed", "closed", "disconnected"):
                    break
                continue
            except asyncio.CancelledError:
                break

            await self._send_event(event)

    async def _send_event(self, event: MoonshineTranscriptEvent) -> None:
        if self._data_channel is None or self._data_channel.readyState != "open":
            logger.debug(
                "webrtc_datachannel_not_ready",
                session_id=self.session_id,
                text=event.text[:40],
            )
            return
        try:
            self._data_channel.send(
                json.dumps(
                    {
                        "type": "transcript_final" if event.is_final else "transcript_partial",
                        "text": event.text,
                        "line_id": event.line_id,
                        "start_time_sec": event.start_time_sec,
                        "duration_sec": event.duration_sec,
                        "latency_ms": event.latency_ms,
                    }
                )
            )
        except Exception as exc:
            logger.warning(
                "webrtc_datachannel_send_failed",
                session_id=self.session_id,
                error=str(exc),
            )

    async def create_answer(self, offer_sdp: str, offer_type: str) -> Dict[str, str]:
        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer_sdp, type=offer_type)
        )
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        return {"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type}

    async def close(self) -> None:
        if self._event_reader is not None:
            self._event_reader.cancel()
            try:
                await self._event_reader
            except asyncio.CancelledError:
                pass
        if self.audio_track is not None:
            await self.audio_track.close()
        if self.moonshine_stream is not None:
            await self.moonshine_stream.close()
        await self.pc.close()
        _connections.pop(self.session_id, None)
        logger.info(
            "webrtc_session_closed",
            session_id=self.session_id,
            duration_sec=round(time.time() - self._start_time, 1),
        )


async def handle_offer(
    engine: MoonshineStreamingEngine,
    session_id: str,
    offer: Dict[str, str],
) -> Dict[str, str]:
    """Create a new WebRTC session from a browser SDP offer."""
    if session_id in _connections:
        old_pc = _connections.pop(session_id)
        await old_pc.close()

    session = await WebRTCSession.create(session_id=session_id, engine=engine)
    _connections[session_id] = session.pc
    answer = await session.create_answer(offer["sdp"], offer["type"])
    logger.info(
        "webrtc_answer_created",
        session_id=session_id,
        answer_type=answer["type"],
    )
    return answer


async def close_all_sessions() -> None:
    """Clean up every active WebRTC session; used during application shutdown."""
    sessions = list(_connections.keys())
    for sid in sessions:
        pc = _connections.pop(sid, None)
        if pc is not None:
            await pc.close()
    _connections.clear()


# References
# [^aiortc]: Holm, J., et al. (2019-). aiortc — WebRTC and ORTC implementation
#             for Python using asyncio. https://github.com/aiortc/aiortc.
# [^Moonshine2026]: Moonshine Voice documentation and benchmark tables, 2026.
# [^scipy]: Virtanen, P., et al. (2020). SciPy 1.0: Fundamental Algorithms for
#           Scientific Computing in Python. *Nature Methods*, 17, 261-272.
