"""
Service Interface Definitions
Hexagonal architecture: domain logic depends on interfaces, not implementations.
Ref: Cockburn 2005, "Hexagonal Architecture".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Optional, List, Dict, Any
from abc import ABC, abstractmethod
import numpy as np

@dataclass
class AudioChunk:
    """Raw PCM audio chunk."""
    samples: np.ndarray  # float32, 16kHz, mono
    timestamp_ms: int
    sample_rate: int = 16000

@dataclass
class TranscriptEvent:
    """ASR output event."""
    text: str
    is_final: bool
    is_speech_final: bool
    confidence: float
    language: Optional[str] = None
    timestamp_ms: int = 0

@dataclass
class LLMToken:
    """Streaming LLM token."""
    text: str
    is_tool_call: bool = False
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None

@dataclass
class AudioOutputChunk:
    """TTS output audio chunk."""
    pcm_bytes: bytes
    sample_rate: int = 24000
    is_sentence_start: bool = False
    is_sentence_end: bool = False

@dataclass
class MemoryQuery:
    """Query to memory system."""
    text: str
    session_id: str
    conversation_history: List[Dict[str, str]]

@dataclass
class MemoryResult:
    """Retrieved context from memory."""
    chunks: List[str]
    sources: List[str]
    cache_hit: bool
    latency_ms: float

# ---------------------------------------------------------------------------
# Ports (Interfaces)
# ---------------------------------------------------------------------------

class STTPort(ABC):
    """
    Automatic Speech Recognition port.
    Ref: Radford et al. 2022; Gandhi et al. 2023.
    ISP: Only the methods actually used by the pipeline are required.
    """
    
    @abstractmethod
    async def transcribe_file(self, audio_path: str) -> TranscriptEvent:
        """Batch transcription for non-real-time use."""
        pass

class TTSPort(ABC):
    """
    Text-to-Speech port.
    Ref: Kim et al. 2021 (VITS); Hansen 2023 (Piper).
    """
    
    @abstractmethod
    async def synthesize_stream(self, text_stream: AsyncIterator[str]) -> AsyncIterator[AudioOutputChunk]:
        """Stream text in, audio chunks out."""
        pass
    
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Batch synthesis for non-streaming use."""
        pass

class LLMPort(ABC):
    """
    Large Language Model port.
    Ref: Yao et al. 2023 (ReAct); OpenAI Function Calling.
    ISP: Only the methods actually used by the pipeline are required.
    """
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Synchronous chat completion with optional tool calling."""
        pass

class MemoryPort(ABC):
    """
    Memory & retrieval port.
    Ref: Qiu et al. 2026 (VoiceAgentRAG); Lewis et al. 2020 (RAG).
    ISP: Only the methods actually used by the pipeline are required.
    """
    
    @abstractmethod
    async def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve relevant context for current turn."""
        pass
    
    @abstractmethod
    async def store_turn(self, session_id: str, role: str, content: str) -> None:
        """Persist turn to long-term memory."""
        pass

class VADPort(ABC):
    """
    Voice Activity Detection port.
    Ref: Silero Team 2024; Rabiner & Sambur 1975.
    """
    
    @abstractmethod
    async def process(self, audio_chunk: AudioChunk) -> Dict[str, Any]:
        """
        Returns: {
            'is_speech': bool,
            'probability': float,
            'speech_start': bool,
            'speech_end': bool
        }
        """
        pass

class TransportPort(ABC):
    """
    Client transport port.
    ADR-001: WebRTC media + WebSocket signaling.
    """
    
    @abstractmethod
    async def send_audio(self, session_id: str, audio: bytes) -> None:
        """Send audio chunk to client."""
        pass
    
    @abstractmethod
    async def receive_audio(self, session_id: str) -> AsyncIterator[AudioChunk]:
        """Receive audio from client."""
        pass


class DomainPort(ABC):
    """
    Domain plugin interface.
    Each vertical domain (Education, Pharma, Construction, Hospitality)
    implements this port to plug into the voice agent pipeline.
    
    Ref: Cockburn 2005 (Hexagonal Architecture) [^42];
         Martin 2002 (OCP/DIP — open for extension, closed for modification) [^94];
         Gamma et al. 1994 (Strategy Pattern — interchangeable algorithms) [^95].
    
    ADR-009: Domain-Modular Voice Agent Platform.
    """

    @property
    @abstractmethod
    def domain_id(self) -> str:
        """Unique domain identifier, e.g., 'construction', 'education'."""
        pass

    @abstractmethod
    def create_receptionist(
        self,
        llm_client: LLMPort,
        tts_provider: Optional[Any] = None,
    ) -> "Receptionist":
        """
        Factory: create a domain-specific Receptionist instance.
        The pipeline injects the LLM client; the domain wires its own
        tools, prompts, and knowledge base.
        Meyer 1988 (Design by Contract): typed return value, not Any [^M1].
        """
        pass

    @abstractmethod
    def get_config(self) -> Any:
        """Domain-specific ReceptionistConfig."""
        pass


# References
# [^1]: Radford, A., et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision. ICML.
# [^3]: Gandhi, S., et al. (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. arXiv:2311.00430.
# [^7]: Kim, J., et al. (2021). Conditional Variational Autoencoder with Adversarial Learning for End-to-End Text-to-Speech. ICML.
# [^13]: OpenAI. (2023). Function Calling API Documentation.
# [^14]: Qiu, J., et al. (2026). VoiceAgentRAG. arXiv:2603.02206.
# [^32]: Rabiner, L. R., & Sambur, M. R. (1975). An Algorithm for Determining the Endpoints of Isolated Utterances. Bell System Technical Journal.
# [^33]: Silero Team. (2024). Silero VAD: Pre-trained enterprise-grade Voice Activity Detector. github.com/snakers4/silero-vad.
# [^37]: Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS.
# [^42]: Cockburn, A. (2005). Hexagonal Architecture. alistair.cockburn.us/hexagonal-architecture/.
# [^45]: IETF. (2012). RFC 6716: Definition of the Opus Audio Codec.
# [^48]: Hansen, S. (2023). Piper: A fast, local neural text-to-speech system. rhasspy.github.io/piper-samples/.
# [^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR.
