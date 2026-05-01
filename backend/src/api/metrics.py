"""
Prometheus Metrics Endpoint
RED metrics for voice agent observability.
Ref: docs/architecture/infrastructure/observability.md
"""

from fastapi import APIRouter
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
CALLS_TOTAL = Counter(
    "voice_agent_calls_total",
    "Total number of calls handled",
    ["status"],
)

TURNS_TOTAL = Counter(
    "voice_agent_turns_total",
    "Total number of conversation turns",
    ["intent"],
)

TOOL_CALLS_TOTAL = Counter(
    "voice_agent_tool_calls_total",
    "Total number of tool executions",
    ["tool_name", "status"],
)

STT_REQUESTS_TOTAL = Counter(
    "voice_agent_stt_requests_total",
    "Total STT requests",
    ["status"],
)

TTS_REQUESTS_TOTAL = Counter(
    "voice_agent_tts_requests_total",
    "Total TTS requests",
    ["status"],
)

# ---------------------------------------------------------------------------
# Histograms (latency distributions)
# ---------------------------------------------------------------------------
TURN_GAP_SECONDS = Histogram(
    "voice_agent_turn_gap_seconds",
    "Time from speech end to first audio byte",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.5, 2.0, 5.0],
)

STT_LATENCY_SECONDS = Histogram(
    "voice_agent_stt_latency_seconds",
    "STT inference latency",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0],
)

LLM_TTFT_SECONDS = Histogram(
    "voice_agent_llm_ttft_seconds",
    "LLM time to first token",
    buckets=[0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0],
)

TTS_TTFB_SECONDS = Histogram(
    "voice_agent_tts_ttfb_seconds",
    "TTS time to first byte",
    buckets=[0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5],
)

TOOL_LATENCY_SECONDS = Histogram(
    "voice_agent_tool_latency_seconds",
    "Tool execution latency",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
)

# ---------------------------------------------------------------------------
# Gauges
# ---------------------------------------------------------------------------
ACTIVE_SESSIONS = Gauge(
    "voice_agent_active_sessions",
    "Number of active call sessions",
)

GPU_UTILIZATION = Gauge(
    "voice_agent_gpu_utilization_percent",
    "GPU utilization percentage",
    ["node", "gpu_index"],
)


@router.get("", response_class=bytes)
async def metrics() -> bytes:
    """Prometheus metrics endpoint."""
    return generate_latest()
