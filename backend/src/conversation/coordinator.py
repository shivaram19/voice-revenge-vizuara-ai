"""
Conversation Coordinator
Orchestrates the full voice pipeline with respect for the conversational floor.
Ref: SigArch 2026 streaming architecture [^16].

Principle: The AI is not a broadcaster. It is a conversational partner.
It coordinates its own speech, listening, and thinking with the user's rhythm.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, Callable, AsyncIterator

from src.conversation.turn_taking import TurnTakingEngine, TurnTakingConfig
from src.streaming.sentence_aggregator import SentenceAggregator


@dataclass
class CoordinatorConfig:
    """Configuration for the conversation coordinator."""
    turn_taking: TurnTakingConfig = None
    enable_backchannels: bool = True
    enable_barge_in: bool = True
    ttfb_target_ms: int = 400           # Time-to-first-byte for AI response
    max_latency_ms: int = 800           # Maximum acceptable latency

    def __post_init__(self):
        if self.turn_taking is None:
            self.turn_taking = TurnTakingConfig()


class ConversationCoordinator:
    """
    Central coordinator for the voice conversation loop.

    Responsibilities:
    1. Manage turn-taking (who speaks when)
    2. Handle barge-in (user interrupts AI)
    3. Inject backchannels (show attentiveness)
    4. Coordinate STT → LLM → TTS pipeline
    5. Respect user's attention and readiness
    """

    def __init__(
        self,
        config: CoordinatorConfig = None,
        stt_provider=None,
        llm_provider=None,
        tts_provider=None,
        turn_engine: TurnTakingEngine = None,
    ):
        self.config = config or CoordinatorConfig()
        self.stt = stt_provider
        self.llm = llm_provider
        self.tts = tts_provider
        self.turns = turn_engine or TurnTakingEngine(self.config.turn_taking)
        self.aggregator = SentenceAggregator()

        # State
        self._is_running = False
        self._current_task: Optional[asyncio.Task] = None
        self._tts_queue: asyncio.Queue = asyncio.Queue()
        self._user_transcript_buffer: str = ""
        self._ai_response_buffer: str = ""

    # -----------------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------------

    async def run(self, audio_input: AsyncIterator[bytes], audio_output: Callable[[bytes], None]):
        """
        Main conversation loop.

        Flow:
        1. Stream audio to STT
        2. STT emits transcript events (partial + final)
        3. On final transcript, send to LLM
        4. LLM streams response tokens
        5. SentenceAggregator chunks tokens into TTS-ready sentences
        6. TTS synthesizes audio
        7. Turn-taking engine decides WHEN to play audio
        8. Backchannels injected during long user turns
        """
        self._is_running = True

        # Start STT stream
        stt_task = asyncio.create_task(self._process_stt(audio_input))

        # Start TTS output loop
        tts_task = asyncio.create_task(self._process_tts(audio_output))

        try:
            await asyncio.gather(stt_task, tts_task)
        except asyncio.CancelledError:
            pass
        finally:
            self._is_running = False

    async def _process_stt(self, audio_input: AsyncIterator[bytes]):
        """Process incoming audio through STT."""
        async for audio_chunk in audio_input:
            # Detect speech start/end via VAD (integrated into STT)
            is_speech = self._detect_speech(audio_chunk)

            if is_speech:
                if self.turns.state.value not in ("USER_SPEAKING", "BOTH_SPEAKING"):
                    self.turns.on_user_speech_start()

                    # If AI was speaking, handle barge-in
                    if self.turns.state.value == "BOTH_SPEAKING":
                        await self._handle_barge_in()
            else:
                if self.turns.state.value in ("USER_SPEAKING", "BOTH_SPEAKING"):
                    self.turns.on_user_speech_end()

                    # Check if we have a final transcript to process
                    if self._user_transcript_buffer:
                        await self._process_user_turn(self._user_transcript_buffer)
                        self._user_transcript_buffer = ""

            # Send to STT for transcription
            # (In production, this would stream to Deepgram/Azure STT)

            # Check for backchannel opportunity
            if self.config.enable_backchannels and self.turns.should_send_backchannel():
                backchannel = self.turns.get_backchannel()
                await self._tts_queue.put({"type": "backchannel", "text": backchannel})

    def _detect_speech(self, audio_chunk: bytes) -> bool:
        """Simple VAD placeholder. Production: integrate Silero VAD [^33]."""
        # Placeholder: assume speech based on energy threshold
        energy = sum(abs(b - 128) for b in audio_chunk) / len(audio_chunk) if audio_chunk else 0
        return energy > 10  # Arbitrary threshold

    async def _handle_barge_in(self):
        """User interrupted the AI. Stop speaking immediately."""
        if not self.config.enable_barge_in:
            return

        result = self.turns.on_barge_in()

        if result["action"] == "ignore":
            return

        # Cancel current TTS playback
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await self._current_task
            except asyncio.CancelledError:
                pass

        # Clear TTS queue
        while not self._tts_queue.empty():
            try:
                self._tts_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Send acknowledgment if persistent interruption
        if result["action"] == "yield_fully":
            await self._tts_queue.put({
                "type": "acknowledgment",
                "text": "I'm listening. Go ahead.",
            })

    async def _process_user_turn(self, transcript: str):
        """Process a completed user turn through the LLM."""
        # Update turn-taking state
        self.turns.on_ai_speech_start()

        # Call LLM with full context
        response_stream = await self.llm.generate_response(transcript)

        # Stream response through sentence aggregator → TTS
        async for token in response_stream:
            sentences = self.aggregator.add_token(token)
            for sentence in sentences:
                # Wait for turn-taking approval before sending to TTS
                if self.turns.should_ai_speak(has_response_ready=True):
                    await self._tts_queue.put({"type": "response", "text": sentence})

        # Flush any remaining text
        remainder = self.aggregator.flush()
        if remainder and self.turns.should_ai_speak(has_response_ready=True):
            await self._tts_queue.put({"type": "response", "text": remainder})

        self.turns.on_ai_speech_end()

    async def _process_tts(self, audio_output: Callable[[bytes], None]):
        """Process TTS queue and output audio."""
        while self._is_running:
            try:
                item = await asyncio.wait_for(self._tts_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            text = item["text"]
            msg_type = item["type"]

            # Synthesize audio
            audio = await self.tts.synthesize(text)

            # For backchannels, play immediately (don't wait for turn)
            if msg_type == "backchannel":
                audio_output(audio)
                continue

            # For responses, respect turn-taking
            if msg_type == "response":
                # Check if user started speaking while we were synthesizing
                if self.turns.state.value in ("USER_SPEAKING", "BOTH_SPEAKING"):
                    # User started speaking; defer this chunk
                    await self._tts_queue.put(item)
                    await asyncio.sleep(0.1)
                    continue

                audio_output(audio)

            elif msg_type == "acknowledgment":
                audio_output(audio)

    # -----------------------------------------------------------------------
    # Public API for manual control
    # -----------------------------------------------------------------------

    async def force_listen(self):
        """Force the AI to stop speaking and listen."""
        await self._handle_barge_in()

    async def inject_message(self, text: str):
        """Inject a system message (e.g., emergency alert)."""
        await self._tts_queue.put({"type": "response", "text": text})

    def get_conversation_stats(self) -> dict:
        """Get conversation statistics."""
        return self.turns.get_stats()


# References
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
# [^33]: Silero Team. (2024). Silero VAD.
