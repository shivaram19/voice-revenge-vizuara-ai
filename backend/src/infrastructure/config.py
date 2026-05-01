"""
Voice Agent Platform Configuration
Research-driven defaults with citation comments.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class ASRConfig:
    """
    ADR-002: Tiered ASR strategy.
    Primary: Distil-Whisper for English (5.8× speedup, <1% WER delta).
    Fallback: Whisper large-v3 for quality-critical.
    Edge: whisper.cpp for offline.
    """
    primary_model: str = "distil-whisper/distil-large-v3"
    fallback_model: str = "openai/whisper-large-v3"
    edge_model: str = "ggml-distil-large-v3.bin"
    
    # Distil-Whisper RTF on GPU A10G: ~0.17× 
    # Target: handle 50 concurrent streams per GPU
    max_concurrent_streams_per_gpu: int = 50
    
    # Fixed-window models have latency floor. Streaming chunk size
    # balances latency vs accuracy.
    # Ref: arXiv:2410.15608 — shorter chunks reduce latency but increase WER
    chunk_length_s: float = 15.0  # Distil-Whisper optimal per paper
    
    # Voice Activity Detection upstream
    vad_model: str = "silero-vad"
    vad_threshold: float = 0.5
    vad_min_silence_ms: int = 300  # 300ms optimal per Deepgram best practices

@dataclass
class TTSConfig:
    """
    ADR-TBD: TTS tiered by deployment target.
    Edge: Piper (7M params, CPU real-time).
    Cloud: Coqui VITS or ElevenLabs for quality.
    """
    edge_engine: str = "piper"
    edge_voice: str = "en_US-lessac-high"
    
    cloud_engine: str = "coqui"
    cloud_model: str = "tts_models/en/vctk/vits"
    
    # Sentence buffering strategy for streaming
    # Ref: SigArch 2026, Section 4.5
    sentence_min_chars: int = 10
    sentence_end_punctuation: str = ".!?"
    
    # Time-to-first-byte target
    ttfb_target_ms: int = 150

@dataclass
class LLMConfig:
    """
    LLM serving via vLLM with continuous batching.
    Ref: Kwon et al. 2023 (SOSP) — PagedAttention.
    """
    model: str = "Qwen/Qwen2.5-7B-Instruct"
    api_base: str = "http://localhost:8000/v1"
    
    # Streaming is mandatory for latency
    stream: bool = True
    
    # TTFT target: 200ms
    # Achieved via: GPU pre-warming, KV cache reuse, prefix caching
    ttft_target_ms: int = 200
    
    # Token throughput target
    tokens_per_second_target: int = 20
    
    # Tool use configuration
    tool_call_timeout_s: int = 2
    max_tool_iterations: int = 3

@dataclass
class MemoryConfig:
    """
    ADR-003: Dual-agent memory router (VoiceAgentRAG).
    Ref: Qiu et al. 2026, arXiv:2603.02206
    """
    # Semantic cache (foreground)
    cache_backend: str = "faiss"
    cache_max_size: int = 2000
    cache_ttl_s: int = 300
    cache_similarity_threshold: float = 0.40
    
    # Vector store (fallback)
    vector_store: str = "qdrant"
    vector_store_url: str = "http://qdrant:6333"
    
    # Slow Thinker prefetch
    prefetch_enabled: bool = True
    prefetch_max_topics: int = 5
    prefetch_top_k: int = 10
    prefetch_rate_limit_s: float = 0.5
    
    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

@dataclass
class StreamingConfig:
    """
    ADR-001: WebRTC for media, WebSocket for signaling.
    """
    transport: str = "webrtc"
    signaling_transport: str = "websocket"
    
    # Audio parameters
    sample_rate: int = 16000
    channels: int = 1
    codec: str = "opus"  # Opus: best voice compression per IETF RFC 6716
    bitrate_kbps: int = 32
    
    # WebRTC-specific
    ice_servers: list = None
    enable_aec: bool = True  # Acoustic Echo Cancellation for barge-in
    enable_agc: bool = True   # Automatic Gain Control
    enable_ns: bool = True    # Noise Suppression

@dataclass
class ScalingConfig:
    """
    Infrastructure scaling targets for 1M concurrent sessions.
    Ref: NVIDIA 2023 Riva autoscaling; Barroso 2018.
    """
    target_concurrent_sessions: int = 1_000_000
    
    # GPU autoscaling
    gpu_autoscale_metric: str = "nv_inference_queue_duration_us"
    gpu_autoscale_target_ms: int = 500
    gpu_min_replicas: int = 10
    gpu_max_replicas: int = 5000
    
    # CPU autoscaling
    cpu_autoscale_metric: str = "cpu_utilization"
    cpu_autoscale_target_pct: int = 70
    
    # Spot instance usage for batch workloads
    spot_instance_ratio: float = 0.3
    
    # Geographic distribution
    regions: list = None

@dataclass
class SarvamConfig:
    """
    Sarvam AI provider config for Indian-language voice sessions.
    STT: Saaras v3 (HTTP batch). TTS: Bulbul v3 (HTTP batch).
    Ref: ADR-002 (tiered ASR); Sarvam AI docs.
    """
    api_key: str = ""
    # STT
    stt_model: str = "saaras:v3"
    stt_mode: str = "codemix"       # handles Tenglish (Telugu+English mixing)
    stt_language: str = "unknown"   # auto-detect across 22 Indian languages
    # TTS
    tts_model: str = "bulbul:v3"
    tts_language: str = "te-IN"     # primary language (Jaya High School, Suryapet)
    tts_speaker_female: str = "kavya"
    tts_speaker_male: str = "rohan"
    tts_sample_rate: int = 22050    # Sarvam native; pipeline resamples to 8kHz μ-law
    tts_pace: float = 0.9           # slightly slower for PSTN clarity
    tts_loudness: float = 1.0
    # Endpointing — Telugu is agglutinative; longer words need relaxed silence detection
    endpointing_map: Optional[dict] = None

    def __post_init__(self):
        if self.endpointing_map is None:
            self.endpointing_map = {
                "te-IN": 750,   # ms — Telugu phonology needs relaxed endpointing
                "hi-IN": 600,
                "ta-IN": 700,
                "en-IN": 500,
            }


@dataclass
class PlatformConfig:
    asr: ASRConfig = None
    tts: TTSConfig = None
    llm: LLMConfig = None
    memory: MemoryConfig = None
    streaming: StreamingConfig = None
    scaling: ScalingConfig = None
    
    def __post_init__(self):
        self.asr = self.asr or ASRConfig()
        self.tts = self.tts or TTSConfig()
        self.llm = self.llm or LLMConfig()
        self.memory = self.memory or MemoryConfig()
        self.streaming = self.streaming or StreamingConfig()
        self.scaling = self.scaling or ScalingConfig()

# References
# [^3]: Gandhi, S., et al. (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. arXiv:2311.00430.
# [^7]: Kim, J., et al. (2021). Conditional Variational Autoencoder with Adversarial Learning for End-to-End Text-to-Speech. ICML.
# [^14]: Qiu, J., et al. (2026). VoiceAgentRAG. arXiv:2603.02206.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
# [^25]: Kwon, W., et al. (2023). Efficient Memory Management for Large Language Model Serving with PagedAttention. SOSP.
# [^30]: Barroso, L. A., et al. (2018). The Datacenter as a Computer: Designing Warehouse-Scale Machines. Morgan & Claypool.
# [^31]: NVIDIA. (2023). Riva Speech AI Skills User Guide. docs.nvidia.com/deeplearning/riva/user-guide/.
# [^45]: Deepgram. (2023). Best Practices for Voice Activity Detection. deepgram.com/learn/vad-best-practices.
# [^45]: IETF. (2012). RFC 6716: Definition of the Opus Audio Codec.
