"""
Azure VoiceLive (GPT-4.1 real-time) Healthcare Assistant
==========================================================
Thin adapter around the Microsoft Foundry VoiceLive SDK that runs the
healthcare patient follow-up agent with native real-time audio.

Goal-Engineering alignment:
  - Objective: capture well-being, medicine adherence, side effects, and
    escalation needs during a post-visit phone call.
  - Constraint: no diagnosis or medical advice; escalate emergencies;
    concise Telugu/English turns.
  - Toolset: this first integration uses instructions only. Native function
    calling via the VoiceLive SDK will be added in a follow-up spike once
    the conversation design is validated.

Prerequisites:
  - azure-ai-voicelive SDK installed (preview package from Microsoft Foundry).
  - AZURE_VOICELIVE_API_KEY and AZURE_VOICELIVE_ENDPOINT environment variables.
  - Working microphone and speakers (pyaudio).

Ref: docs/engineering/goal-vector-healthcare-mvp.md
"""

from __future__ import annotations

import asyncio
import base64
import logging
import queue
from typing import Any, cast

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential

logger = logging.getLogger(__name__)

# Lazy import of the preview SDK so that importing this module does not fail
# when the package is not installed (e.g. in CI or during unit-test collection).
try:
    from azure.ai.voicelive.aio import connect
    from azure.ai.voicelive.models import (
        AudioEchoCancellation,
        AudioNoiseReduction,
        AzureStandardVoice,
        InputAudioFormat,
        Modality,
        OutputAudioFormat,
        RequestSession,
        ServerEventType,
        ServerVad,
    )

    VOICELIVE_AVAILABLE = True
except Exception as _exc:  # pragma: no cover - SDK may not be installed
    VOICELIVE_AVAILABLE = False
    connect = None
    AudioEchoCancellation = None
    AudioNoiseReduction = None
    AzureStandardVoice = None
    InputAudioFormat = None
    Modality = None
    OutputAudioFormat = None
    RequestSession = None
    ServerEventType = None
    ServerVad = None

try:
    import pyaudio
except Exception as _exc:  # pragma: no cover - pyaudio may not be installed
    pyaudio = None


class VoiceLiveAudioProcessor:
    """
    Handles real-time audio capture and playback for the VoiceLive assistant.

    Threading Architecture:
    - Main thread: event loop and event processing.
    - Capture callback thread: PyAudio input stream reads microphone data.
    - Playback callback thread: PyAudio output stream writes received audio.
    """

    loop: asyncio.AbstractEventLoop

    class AudioPlaybackPacket:
        """Packet queued for audio playback."""

        def __init__(self, seq_num: int, data: bytes | None) -> None:
            self.seq_num = seq_num
            self.data = data

    def __init__(self, connection) -> None:
        if pyaudio is None:
            raise RuntimeError("pyaudio is required for VoiceLive audio I/O.")
        self.connection = connection
        self.audio = pyaudio.PyAudio()

        # VoiceLive expects PCM16, 24 kHz, mono.
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 24000
        self.chunk_size = 1200  # 50 ms

        self.input_stream: pyaudio.Stream | None = None
        self.output_stream: pyaudio.Stream | None = None
        self.playback_queue: queue.Queue[VoiceLiveAudioProcessor.AudioPlaybackPacket] = queue.Queue()
        self.playback_base = 0
        self.next_seq_num = 0

        logger.info("VoiceLiveAudioProcessor initialized (24kHz PCM16 mono)")

    def start_capture(self) -> None:
        """Start capturing microphone audio and streaming it to VoiceLive."""

        def _capture_callback(in_data, _frame_count, _time_info, _status_flags):
            audio_base64 = base64.b64encode(in_data).decode("utf-8")
            asyncio.run_coroutine_threadsafe(
                self.connection.input_audio_buffer.append(audio=audio_base64), self.loop
            )
            return (None, pyaudio.paContinue)

        if self.input_stream:
            return

        self.loop = asyncio.get_event_loop()
        try:
            self.input_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=_capture_callback,
            )
            logger.info("Started audio capture")
        except Exception:
            logger.exception("Failed to start audio capture")
            raise

    def start_playback(self) -> None:
        """Initialize audio playback stream."""
        if self.output_stream:
            return

        remaining = b""

        def _playback_callback(_in_data, frame_count, _time_info, _status_flags):
            nonlocal remaining
            frame_count *= pyaudio.get_sample_size(pyaudio.paInt16)

            out = remaining[:frame_count]
            remaining = remaining[frame_count:]

            while len(out) < frame_count:
                try:
                    packet = self.playback_queue.get_nowait()
                except queue.Empty:
                    out = out + bytes(frame_count - len(out))
                    continue
                except Exception:
                    logger.exception("Error in audio playback")
                    raise

                if packet is None or packet.data is None:
                    logger.info("End of playback queue.")
                    break

                if packet.seq_num < self.playback_base:
                    if remaining:
                        remaining = b""
                    continue

                num_to_take = frame_count - len(out)
                out = out + packet.data[:num_to_take]
                remaining = packet.data[num_to_take:]

            if len(out) >= frame_count:
                return (out, pyaudio.paContinue)
            return (out, pyaudio.paComplete)

        try:
            self.output_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                output=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=_playback_callback,
            )
            logger.info("Audio playback system ready")
        except Exception:
            logger.exception("Failed to initialize audio playback")
            raise

    def _get_and_increase_seq_num(self) -> int:
        seq = self.next_seq_num
        self.next_seq_num += 1
        return seq

    def queue_audio(self, audio_data: bytes | None) -> None:
        """Queue audio data for playback."""
        self.playback_queue.put(
            VoiceLiveAudioProcessor.AudioPlaybackPacket(
                seq_num=self._get_and_increase_seq_num(),
                data=audio_data,
            )
        )

    def skip_pending_audio(self) -> None:
        """Skip current audio in playback queue (used for barge-in)."""
        self.playback_base = self._get_and_increase_seq_num()

    def shutdown(self) -> None:
        """Clean up audio resources."""
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None
            logger.info("Stopped audio capture")

        if self.output_stream:
            self.skip_pending_audio()
            self.queue_audio(None)
            self.output_stream.stop_stream()
            self.output_stream.close()
            self.output_stream = None
            logger.info("Stopped audio playback")

        if self.audio:
            self.audio.terminate()
            logger.info("Audio processor cleaned up")


class HealthcareVoiceLiveAssistant:
    """
    Healthcare-specific wrapper around the Azure VoiceLive real-time API.

    Injects the goal-engineered follow-up instructions and manages the
    audio/event lifecycle.
    """

    def __init__(
        self,
        endpoint: str,
        credential: AzureKeyCredential | AsyncTokenCredential,
        model: str,
        voice: str,
        instructions: str,
    ) -> None:
        if not VOICELIVE_AVAILABLE:
            raise RuntimeError(
                "azure-ai-voicelive SDK is not installed. "
                "Install the preview package from Microsoft Foundry to use this assistant."
            )
        self.endpoint = endpoint
        self.credential = credential
        self.model = model
        self.voice = voice
        self.instructions = instructions
        self.connection: Any | None = None
        self.audio_processor: VoiceLiveAudioProcessor | None = None
        self.session_ready = False
        self._active_response = False
        self._response_api_done = False

    async def start(self) -> None:
        """Start the real-time voice assistant session."""
        try:
            logger.info("Connecting to VoiceLive API with model %s", self.model)
            async with connect(
                endpoint=self.endpoint,
                credential=self.credential,
                model=self.model,
            ) as connection:
                self.connection = connection
                self.audio_processor = VoiceLiveAudioProcessor(connection)
                await self._setup_session()
                self.audio_processor.start_playback()
                await self._process_events()
        finally:
            if self.audio_processor:
                self.audio_processor.shutdown()

    async def _setup_session(self) -> None:
        """Configure the VoiceLive session with healthcare instructions."""
        logger.info("Setting up VoiceLive session...")

        if self.voice.startswith("en-US-") or self.voice.startswith("en-CA-") or "-" in self.voice:
            voice_config = AzureStandardVoice(name=self.voice)
        else:
            voice_config = self.voice

        turn_detection = ServerVad(
            threshold=0.5,
            prefix_padding_ms=300,
            silence_duration_ms=500,
        )

        session_config = RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=self.instructions,
            voice=voice_config,
            input_audio_format=InputAudioFormat.PCM16,
            output_audio_format=OutputAudioFormat.PCM16,
            turn_detection=turn_detection,
            input_audio_echo_cancellation=AudioEchoCancellation(),
            input_audio_noise_reduction=AudioNoiseReduction(type="azure_deep_noise_suppression"),
        )

        conn = self.connection
        assert conn is not None
        await conn.session.update(session=session_config)
        logger.info("Session configuration sent")

    async def _process_events(self) -> None:
        """Process events from the VoiceLive connection."""
        try:
            conn = self.connection
            assert conn is not None
            async for event in conn:
                await self._handle_event(event)
        except Exception:
            logger.exception("Error processing events")
            raise

    async def _handle_event(self, event) -> None:
        """Handle VoiceLive server events."""
        ap = self.audio_processor
        conn = self.connection
        assert ap is not None
        assert conn is not None

        if event.type == ServerEventType.SESSION_UPDATED:
            logger.info("Session ready: %s", event.session.id)
            self.session_ready = True
            ap.start_capture()
            print("\n" + "=" * 60)
            print("🏥 Healthcare Follow-Up Agent Ready")
            print("Start speaking. Press Ctrl+C to exit.")
            print("=" * 60 + "\n")

        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            logger.info("User started speaking")
            print("🎤 Listening...")
            ap.skip_pending_audio()
            if self._active_response and not self._response_api_done:
                try:
                    await conn.response.cancel()
                    logger.debug("Cancelled in-progress response due to barge-in")
                except Exception as e:
                    if "no active response" in str(e).lower():
                        logger.debug("Cancel ignored - response already completed")
                    else:
                        logger.warning("Cancel failed: %s", e)

        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            logger.info("User stopped speaking")
            print("🤔 Processing...")

        elif event.type == ServerEventType.RESPONSE_CREATED:
            logger.info("Assistant response created")
            self._active_response = True
            self._response_api_done = False

        elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
            logger.debug("Received audio delta")
            ap.queue_audio(event.delta)

        elif event.type == ServerEventType.RESPONSE_AUDIO_DONE:
            logger.info("Assistant finished speaking")
            print("🎤 Ready for next input...")

        elif event.type == ServerEventType.RESPONSE_DONE:
            logger.info("Response complete")
            self._active_response = False
            self._response_api_done = True

        elif event.type == ServerEventType.ERROR:
            msg = event.error.message
            if "Cancellation failed: no active response" in msg:
                logger.debug("Benign cancellation error: %s", msg)
            else:
                logger.error("VoiceLive error: %s", msg)
                print(f"Error: {msg}")

        elif event.type == ServerEventType.CONVERSATION_ITEM_CREATED:
            logger.debug("Conversation item created: %s", event.item.id)

        else:
            logger.debug("Unhandled event type: %s", event.type)


def check_audio_devices() -> bool:
    """Verify that at least one input and one output device are available."""
    if pyaudio is None:
        print("❌ pyaudio is not installed.")
        return False
    try:
        p = pyaudio.PyAudio()
        input_devices = [
            i
            for i in range(p.get_device_count())
            if cast(int, p.get_device_info_by_index(i).get("maxInputChannels", 0)) > 0
        ]
        output_devices = [
            i
            for i in range(p.get_device_count())
            if cast(int, p.get_device_info_by_index(i).get("maxOutputChannels", 0)) > 0
        ]
        p.terminate()
        if not input_devices:
            print("❌ No audio input devices found. Please check your microphone.")
            return False
        if not output_devices:
            print("❌ No audio output devices found. Please check your speakers.")
            return False
        return True
    except Exception as exc:
        print(f"❌ Audio system check failed: {exc}")
        return False
