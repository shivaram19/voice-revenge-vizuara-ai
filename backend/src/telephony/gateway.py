"""
Abstract Telephony Gateway Interface
DIP: Domain logic depends on this abstraction, not Twilio concretions.
Ref: Twilio (2024). Media Streams API [^43].
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable


@dataclass
class CallMetadata:
    """Normalized call metadata, provider-agnostic."""
    call_sid: str
    stream_sid: Optional[str]
    from_number: str
    to_number: str
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioConfig:
    """Audio pipeline configuration."""
    inbound_sample_rate: int = 8000
    inbound_codec: str = "mulaw"
    stt_sample_rate: int = 16000
    tts_sample_rate: int = 24000
    outbound_sample_rate: int = 8000
    chunk_duration_ms: int = 20


class TelephonyGateway(ABC):
    """
    Abstract gateway for telephony integration.
    Implementations: TwilioGateway, PlivoGateway, TelnyxGateway, etc.
    """

    @property
    @abstractmethod
    def audio_config(self) -> AudioConfig:
        """Return audio configuration for this gateway."""
        pass

    @abstractmethod
    def decode_inbound(self, audio_bytes: bytes) -> bytes:
        """Convert inbound telephony audio to STT-ready PCM."""
        pass

    @abstractmethod
    def encode_outbound(self, pcm_bytes: bytes) -> bytes:
        """Convert TTS PCM to outbound telephony audio format."""
        pass

    @abstractmethod
    def parse_start_message(self, event: Dict[str, Any]) -> CallMetadata:
        """Extract call metadata from provider's start event."""
        pass

    @abstractmethod
    def create_stream_message(self, media_payload: str) -> Dict[str, Any]:
        """Create a media message for the provider."""
        pass

    @abstractmethod
    def create_mark_message(self, mark_name: str) -> Dict[str, Any]:
        """Create a mark message for tracking playback."""
        pass


# References
# [^43]: Twilio. (2024). Media Streams API Documentation.
