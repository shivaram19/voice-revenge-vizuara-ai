"""
Twilio Telephony Gateway — Concrete Implementation
Implements TelephonyGateway for Twilio Media Streams.
Ref: ITU-T G.711 (1972) [^38]; Twilio (2024) [^43].
"""

from typing import Dict, Any, Optional

from src.telephony.gateway import TelephonyGateway, AudioConfig, CallMetadata
from src.telephony._audio_compat import ulaw2lin, lin2ulaw, ratecv


class TwilioGateway(TelephonyGateway):
    """
    Handles audio format conversion between PSTN and voice pipeline.
    Stateless per-call.
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        self._config = config or AudioConfig()

    @property
    def audio_config(self) -> AudioConfig:
        return self._config

    def decode_inbound(self, audio_bytes: bytes) -> bytes:
        """
        Convert Twilio mulaw chunk to 16kHz PCM int16.
        Ref: μ-law companding: 8-bit nonlinear → 16-bit linear PCM [^38].
        """
        linear_8k = ulaw2lin(audio_bytes, 2)
        linear_16k, _ = ratecv(
            linear_8k,
            2,
            1,
            self._config.inbound_sample_rate,
            self._config.stt_sample_rate,
            None,
        )
        return linear_16k

    def encode_outbound(self, pcm_bytes: bytes) -> bytes:
        """
        Convert TTS PCM (24kHz int16) to 8kHz mulaw for Twilio.
        Ref: Downsampling requires anti-aliasing at 4kHz Nyquist [^50].
        """
        linear_8k, _ = ratecv(
            pcm_bytes,
            2,
            1,
            self._config.tts_sample_rate,
            self._config.outbound_sample_rate,
            None,
        )
        return lin2ulaw(linear_8k, 2)

    def parse_start_message(self, event: Dict[str, Any]) -> CallMetadata:
        """Extract call metadata from Twilio start event."""
        start = event.get("start", {})
        return CallMetadata(
            call_sid=start.get("callSid"),
            stream_sid=event.get("streamSid"),
            from_number=start.get("from"),
            to_number=start.get("to"),
        )

    def create_stream_message(self, media_payload: str) -> Dict[str, Any]:
        return {
            "event": "media",
            "media": {"payload": media_payload},
        }

    def create_mark_message(self, mark_name: str) -> Dict[str, Any]:
        return {
            "event": "mark",
            "mark": {"name": mark_name},
        }


# References
# [^38]: ITU-T. (1972). G.711: Pulse Code Modulation (PCM) of Voice Frequencies.
# [^43]: Twilio. (2024). Media Streams API Documentation.
# [^50]: SciPy. (2023). scipy.signal.resample_poly Documentation.
