"""
Deepgram Client Adapter
Implements STTPort and TTSPort using Deepgram's HTTP API.
No SDK dependency — pure asyncio + aiohttp for minimal footprint.

Products used:
  - Nova-3: ASR (real-time streaming + batch) [^6]
  - Aura:  TTS (low-latency voice synthesis)

Ref: Deepgram. (2024). Nova-3 Speech-to-Text API Documentation.
     Deepgram. (2024). Aura Text-to-Speech API Documentation.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Optional, List, Dict, Any

from src.infrastructure.interfaces import STTPort, TTSPort, AudioChunk, TranscriptEvent, AudioOutputChunk


@dataclass
class DeepgramConfig:
    """Deepgram API configuration."""
    api_key: str
    base_url: str = "https://api.deepgram.com/v1"
    stt_model: str = "nova-3"           # Nova-3: best accuracy [^6]
    stt_language: str = "en-US"
    tts_model: str = "aura"             # Aura: low-latency TTS
    tts_voice: str = "aura-asteria-en"  # Default female voice
    enable_punctuation: bool = True
    enable_diarization: bool = False
    vad_turnoff: int = 300              # 300ms silence = utterance end


class DeepgramSTT(STTPort):
    """
    Deepgram Nova-3 Speech-to-Text adapter.
    Supports both batch (file) and streaming (real-time) transcription.
    """

    def __init__(self, config: DeepgramConfig):
        self.config = config
        self._headers = {
            "Authorization": f"Token {config.api_key}",
            "Content-Type": "application/json",
        }

    async def stream_audio(self, audio: AsyncIterator[AudioChunk]) -> AsyncIterator[TranscriptEvent]:
        """
        Stream audio to Deepgram via WebSocket.
        Returns streaming transcript events (partial + final).
        """
        import aiohttp

        ws_url = (
            f"wss://api.deepgram.com/v1/listen"
            f"?model={self.config.stt_model}"
            f"&language={self.config.stt_language}"
            f"&punctuate={str(self.config.enable_punctuation).lower()}"
            f"&interim_results=true"
            f"&utterance_end_ms={self.config.vad_turnoff}"
            f"&encoding=linear16"
            f"&sample_rate=16000"
            f"&channels=1"
        )

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, headers=self._headers) as ws:
                # Producer: stream audio chunks
                async def send_audio():
                    async for chunk in audio:
                        await ws.send_bytes(chunk.samples.tobytes())
                    await ws.send_str('{"type": "CloseStream"}')

                # Consumer: receive transcript events
                sender = asyncio.create_task(send_audio())
                try:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            yield self._parse_response(data)
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            break
                finally:
                    sender.cancel()
                    try:
                        await sender
                    except asyncio.CancelledError:
                        pass

    async def transcribe_file(self, audio_path: str) -> TranscriptEvent:
        """Batch transcription of an audio file."""
        import aiohttp

        url = f"{self.config.base_url}/listen"
        params = {
            "model": self.config.stt_model,
            "language": self.config.stt_language,
            "punctuate": str(self.config.enable_punctuation).lower(),
        }

        async with aiohttp.ClientSession() as session:
            with open(audio_path, "rb") as f:
                async with session.post(
                    url, headers=self._headers, params=params, data=f
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return self._parse_response(data)

    def _parse_response(self, data: Dict[str, Any]) -> TranscriptEvent:
        """Normalize Deepgram response to TranscriptEvent."""
        channel = data.get("channel", {})
        alt = channel.get("alternatives", [{}])[0]

        # Determine if final
        is_final = data.get("is_final", True)
        speech_final = data.get("speech_final", is_final)

        return TranscriptEvent(
            text=alt.get("transcript", ""),
            is_final=is_final,
            is_speech_final=speech_final,
            confidence=alt.get("confidence", 0.0),
            language=data.get("language", self.config.stt_language),
            timestamp_ms=data.get("start", 0),
        )


class DeepgramTTS(TTSPort):
    """
    Deepgram Aura Text-to-Speech adapter.
    Supports streaming synthesis for real-time voice responses.
    """

    def __init__(self, config: DeepgramConfig):
        self.config = config
        self._headers = {
            "Authorization": f"Token {config.api_key}",
            "Content-Type": "application/json",
        }

    async def synthesize_stream(self, text_stream: AsyncIterator[str]) -> AsyncIterator[AudioOutputChunk]:
        """
        Stream text to Deepgram Aura and receive audio chunks.
        Aura returns raw audio bytes (linear16, 24kHz).
        """
        import aiohttp

        url = f"{self.config.base_url}/speak"
        params = {"model": self.config.tts_model}

        async with aiohttp.ClientSession() as session:
            # Accumulate sentences, then synthesize
            buffer = ""
            async for text in text_stream:
                buffer += text
                if text.endswith((".", "!", "?", "\n")) and len(buffer.strip()) > 10:
                    async for chunk in self._synthesize_chunk(session, url, params, buffer.strip()):
                        yield chunk
                    buffer = ""

            if buffer.strip():
                async for chunk in self._synthesize_chunk(session, url, params, buffer.strip()):
                    yield chunk

    async def _synthesize_chunk(
        self,
        session: Any,
        url: str,
        params: Dict[str, str],
        text: str,
    ) -> AsyncIterator[AudioOutputChunk]:
        """Synthesize a single text chunk via Deepgram Aura."""
        payload = {
            "text": text,
            "voice": self.config.tts_voice,
            "encoding": "linear16",
            "sample_rate": 24000,
        }

        async with session.post(
            url, headers=self._headers, params=params, json=payload
        ) as resp:
            resp.raise_for_status()
            # Aura returns audio as a stream or single blob depending on endpoint
            audio_data = await resp.read()
            yield AudioOutputChunk(
                pcm_bytes=audio_data,
                sample_rate=24000,
                is_sentence_start=True,
                is_sentence_end=True,
            )

    async def synthesize(self, text: str) -> bytes:
        """Batch synthesis of a single text string."""
        import aiohttp

        url = f"{self.config.base_url}/speak"
        params = {"model": self.config.tts_model}
        payload = {
            "text": text,
            "voice": self.config.tts_voice,
            "encoding": "linear16",
            "sample_rate": 24000,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=self._headers, params=params, json=payload
            ) as resp:
                resp.raise_for_status()
                return await resp.read()


# References
# [^6]: Deepgram. (2024). Nova-3: Next-Generation Speech-to-Text. deepgram.com/nova-3.
