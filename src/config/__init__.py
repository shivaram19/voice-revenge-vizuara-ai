"""
Configuration Module — Interface Segregation Principle
Each config class has ONE reason to change.
Ref: Microsoft (2024). Azure Identity SDK [^44].
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OpenAIConfig:
    """Azure OpenAI configuration."""
    endpoint: str
    key: str
    deployment: str = "gpt-4o-mini"
    api_version: str = "2024-06-01"

    def validate(self) -> list[str]:
        missing = []
        if not self.endpoint:
            missing.append("openai_endpoint")
        if not self.key:
            missing.append("openai_key")
        return missing


@dataclass(frozen=True)
class DeepgramConfig:
    """Deepgram API configuration. Nova-3 STT + Aura TTS."""
    api_key: str
    stt_model: str = "nova-3"
    stt_language: str = "en-US"
    tts_model: str = "aura"
    tts_voice: str = "aura-asteria-en"
    enable_punctuation: bool = True
    vad_turnoff_ms: int = 300

    def validate(self) -> list[str]:
        missing = []
        if not self.api_key:
            missing.append("deepgram_api_key")
        return missing


@dataclass(frozen=True)
class RedisConfig:
    """Redis cache configuration."""
    host: str
    port: int = 6379
    key: str = ""
    ssl: bool = False

    def validate(self) -> list[str]:
        missing = []
        if not self.host:
            missing.append("redis_host")
        return missing


@dataclass(frozen=True)
class TwilioConfig:
    """Twilio telephony configuration."""
    account_sid: str
    auth_token: str

    def validate(self) -> list[str]:
        missing = []
        if not self.account_sid:
            missing.append("twilio_account_sid")
        if not self.auth_token:
            missing.append("twilio_auth_token")
        return missing


@dataclass(frozen=True)
class AppConfig:
    """Application-level configuration."""
    env: str = "dev"
    log_level: str = "info"
    company_name: str = "BuildPro Contracting"
    business_hours: str = "Monday through Friday, 8 AM to 6 PM. Emergency dispatch 24/7."


@dataclass(frozen=True)
class ObservabilityConfig:
    """Monitoring and observability configuration."""
    appinsights_connection_string: Optional[str] = None


# References
# [^44]: Microsoft. (2024). Azure Identity SDK.
