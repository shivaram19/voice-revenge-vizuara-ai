"""
Azure Application Insights Telemetry
====================================
OpenTelemetry-based distributed tracing and structured metrics for the
voice agent platform. Every call gets a trace; every turn gets a span.

Research Provenance:
    - azure-monitor-opentelemetry: GA, feature parity with Classic SDK [^AM1]
    - OpenTelemetry: de-facto standard for voice agent observability [^HM1]
    - Hamming AI canonical span hierarchy: voice_turn → stt / llm / tts [^HM1]
    - Telnyx 5-metric minimal observability: user_speech_end, first_token,
      first_audio, barge_in_latency, false_endpoint_rate [^TN1]
    - Azure Monitor OpenTelemetry Distro v1.8.7: instrumentation_options dict
      controls enablement per library; the `instrumentations=` kwarg is NOT
      used by _default_instrumentation_options() [^AM2]
    - opentelemetry-instrumentation-asgi wraps ASGI apps and adds span
      context propagation; FastAPI auto-instrumentation injects middleware
      that can interfere with WebSocket connection lifecycle [^OT2]
    - Sampling ratio 1.0 in voice agents: every call must be traceable for
      compliance debugging (PCI-DSS req 10.1) [^PCI]
    - Lazy import pattern: avoids ImportError in dev environments where
      azure-monitor-opentelemetry is not installed [^PEP8]

Environment:
    APPLICATIONINSIGHTS_CONNECTION_STRING — required for telemetry emission
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional

from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_NAMESPACE

from src.infrastructure.pii_redaction import redact_phone, redact_text
from src.infrastructure.logging_config import get_logger

# Lazy import azure-monitor-opentelemetry — not required for local dev [^PEP8]
_configure_azure_monitor = None


def _get_configure_azure_monitor():
    global _configure_azure_monitor
    if _configure_azure_monitor is None:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor as cam
            _configure_azure_monitor = cam
        except ImportError:
            _configure_azure_monitor = False
    return _configure_azure_monitor


# ---------------------------------------------------------------------------
# Global telemetry handles (initialized on first use)
# ---------------------------------------------------------------------------

_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None
_initialized = False


def init_telemetry(service_name: str = "voice-agent-api") -> Dict[str, Any]:
    """
    Initialize Azure Monitor OpenTelemetry Distro.
    Idempotent — safe to call multiple times.
    """
    global _tracer, _meter, _initialized

    if _initialized:
        return {"tracer": _tracer, "meter": _meter}

    conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn_str:
        # Telemetry disabled — return no-op handles [^OT1]
        _tracer = trace.get_tracer(service_name)
        _meter = metrics.get_meter(service_name)
        _initialized = True
        return {"tracer": _tracer, "meter": _meter, "enabled": False}

    cam = _get_configure_azure_monitor()
    if not cam:
        logger = get_logger("telemetry")
        logger.warning("azure_monitor_not_installed", connection_string_present=True)
        _tracer = trace.get_tracer(service_name)
        _meter = metrics.get_meter(service_name)
        _initialized = True
        return {"tracer": _tracer, "meter": _meter, "enabled": False}

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_NAMESPACE: "voice-agent-platform",
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "production"),
            "service.version": os.getenv("APP_VERSION", "0.1.0"),
            "host.name": os.getenv("HOSTNAME", "unknown"),
        }
    )

    # instrumentation_options controls which libraries are instrumented.
    # The `instrumentations=` kwarg is NOT used for this purpose — it is
    # ignored by _default_instrumentation_options() in the distro [^AM2].
    # FastAPI instrumentation MUST remain disabled: it wraps ASGI WebSocket
    # handlers and force-closes connections after ~600 ms of "idle" time
    # while TTS is synthesizing [^OT2]. See DFS-006 and ADR-012.
    try:
        cam(
            connection_string=conn_str,
            resource=resource,
            enable_live_metrics=True,
            disable_offline_storage=False,
            sampling_ratio=1.0,  # Full sampling for compliance debugging [^PCI]
            instrumentation_options={
                "fastapi": {"enabled": False},   # Disables ASGI WS interference [^OT2]
                "urllib3": {"enabled": True},    # HTTP client tracing [^AM1]
                "requests": {"enabled": True},   # HTTP client tracing [^AM1]
            },
        )
    except Exception:
        # Telemetry must never break the application — defensive coding [^HM1]
        logger = get_logger("telemetry")
        logger.warning("azure_monitor_init_failed", connection_string_present=True)
        _tracer = trace.get_tracer(service_name)
        _meter = metrics.get_meter(service_name)
        _initialized = True
        return {"tracer": _tracer, "meter": _meter, "enabled": False}

    _tracer = trace.get_tracer(service_name)
    _meter = metrics.get_meter(service_name)
    _initialized = True

    return {"tracer": _tracer, "meter": _meter, "enabled": True}


def get_tracer() -> trace.Tracer:
    """Return the global tracer (initializes if needed)."""
    if _tracer is None:
        init_telemetry()
    return _tracer  # type: ignore[return-value]


def get_meter() -> metrics.Meter:
    """Return the global meter (initializes if needed)."""
    if _meter is None:
        init_telemetry()
    return _meter  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Custom metrics
# ---------------------------------------------------------------------------

def _ensure_metrics() -> None:
    """Lazy-init counters / histograms."""
    global _call_counter, _turn_counter, _latency_histogram, _barge_in_counter
    if "_call_counter" not in globals():
        meter = get_meter()
        _call_counter = meter.create_counter(
            "voice.calls.total",
            description="Total voice calls handled",
        )
        _turn_counter = meter.create_counter(
            "voice.turns.total",
            description="Total conversation turns",
        )
        _latency_histogram = meter.create_histogram(
            "voice.latency.ms",
            description="End-to-end stage latency in ms",
        )
        _barge_in_counter = meter.create_counter(
            "voice.barge_in.total",
            description="Total barge-in events detected",
        )


# ---------------------------------------------------------------------------
# Voice event logging helpers
# ---------------------------------------------------------------------------

def log_voice_event(
    event_name: str,
    session_id: str,
    properties: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a structured voice event as a span event.
    Appears in Application Insights traces table with customDimensions.
    """
    try:
        current_span = trace.get_current_span()
        current_span.set_attribute("call.session_id", session_id)
        current_span.set_attribute("call.event", event_name)

        if properties:
            for key, value in properties.items():
                current_span.set_attribute(f"call.prop.{key}", str(value))

        event_attrs: Dict[str, Any] = {"session_id": session_id}
        if properties:
            event_attrs.update(properties)

        current_span.add_event(name=event_name, attributes=event_attrs)
    except Exception:
        # Telemetry must never break the call — defensive coding [^HM1]
        pass


def log_call_start(
    session_id: str,
    from_number: str,
    to_number: str,
    domain: str,
) -> None:
    """Log call start event."""
    _ensure_metrics()
    safe_from = redact_phone(from_number)
    safe_to = redact_phone(to_number)

    log_voice_event(
        "call.started",
        session_id,
        {
            "from_number": safe_from,
            "to_number": safe_to,
            "domain": domain,
        },
    )
    try:
        _call_counter.add(1, {"domain": domain, "direction": "inbound"})
    except Exception:
        pass


def log_call_end(
    session_id: str,
    turn_count: int,
    duration_sec: float,
) -> None:
    """Log call end event."""
    log_voice_event(
        "call.ended",
        session_id,
        {
            "turn_count": turn_count,
            "duration_sec": round(duration_sec, 1),
        },
    )


def log_stt_transcript(
    session_id: str,
    transcript: str,
    is_final: bool,
    confidence: float,
) -> None:
    """Log STT transcript (PII-redacted length only)."""
    safe_text = redact_text(transcript[:500]) if transcript else ""

    log_voice_event(
        "stt.transcript",
        session_id,
        {
            "is_final": is_final,
            "confidence": round(confidence, 3),
            "transcript_length": len(transcript),
        },
    )


def log_llm_response(
    session_id: str,
    response_text: str,
    latency_ms: float,
    model: str,
) -> None:
    """Log LLM response generation."""
    _ensure_metrics()
    log_voice_event(
        "llm.response",
        session_id,
        {
            "latency_ms": round(latency_ms, 1),
            "model": model,
            "response_length": len(response_text),
        },
    )
    try:
        _latency_histogram.record(latency_ms, {"stage": "llm", "model": model})
        _turn_counter.add(1, {"domain": "all"})
    except Exception:
        pass


def log_tts_synthesis(
    session_id: str,
    voice_model: str,
    latency_ms: float,
    text_length: int,
) -> None:
    """Log TTS synthesis event."""
    log_voice_event(
        "tts.synthesis",
        session_id,
        {
            "voice_model": voice_model,
            "latency_ms": round(latency_ms, 1),
            "text_length": text_length,
        },
    )
    try:
        _latency_histogram.record(latency_ms, {"stage": "tts", "voice": voice_model})
    except Exception:
        pass


def log_barge_in(session_id: str, recovery_ms: Optional[float] = None) -> None:
    """Log barge-in detection."""
    _ensure_metrics()
    props: Dict[str, Any] = {}
    if recovery_ms is not None:
        props["recovery_ms"] = round(recovery_ms, 1)

    log_voice_event("stt.barge_in", session_id, props)
    try:
        _barge_in_counter.add(1, {"session_id": session_id})
    except Exception:
        pass


def log_exception(
    exception: Exception,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an exception with full stack trace to Application Insights."""
    try:
        current_span = trace.get_current_span()
        if session_id:
            current_span.set_attribute("call.session_id", session_id)
        if context:
            for key, value in context.items():
                current_span.set_attribute(f"error.context.{key}", str(value))
        current_span.record_exception(exception)
        current_span.set_status(
            Status(StatusCode.ERROR, description=str(exception))
        )
    except Exception:
        pass


# References
# [^AM1]: Microsoft Azure Monitor Docs. (2026). OpenTelemetry Distro GA.
# [^AM2]: Microsoft. (2024). Azure Monitor OpenTelemetry Distro v1.8.7 source.
#          azure/monitor/opentelemetry/_utils/configurations.py:_default_instrumentation_options()
#          Confirmed via source-code audit: instrumentations= kwarg is ignored;
#          instrumentation_options dict is the only control surface.
# [^HM1]: Hamming AI. (2026). Monitor Pipecat Agents in Production.
# [^TN1]: Telnyx. (2026). How to Evaluate Voice AI.
# [^OT1]: OpenTelemetry. (2024). W3C Trace Context. opentelemetry.io/docs/concepts/signals/traces/
# [^OT2]: OpenTelemetry Python Contrib. (2024). opentelemetry-instrumentation-asgi.
#          ASGI middleware wraps applications; FastAPIInstrumentor auto-detects FastAPI
#          and injects span-wrapping middleware that can close idle WebSocket connections.
# [^PCI]: PCI Security Standards Council. (2024). PCI-DSS v4.0 Requirement 10.1:
#          Implement audit trails linking all system access to individual users.
# [^PEP8]: van Rossum, G., Warsaw, B., & Coghlan, N. (2001). PEP 8 — Style Guide for Python Code.
#           python.org/dev/peps/pep-0008/
