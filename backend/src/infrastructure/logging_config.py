"""
Structured Logging Configuration
================================
JSON-structured logs in production; pretty console in dev.
Correlates with OpenTelemetry trace_id / span_id for distributed tracing.

Research Provenance:
    - structlog: separation of log emission from rendering [^SL1]
    - OpenTelemetry: W3C traceparent propagation across services [^OT1]
    - Azure Monitor: maps OTel spans → App Insights traces/metrics [^AM1]
    - DFS-007 / ADR-013: every conversation event needs millisecond
      timestamps + t_ms_since_call_start so post-hoc analysis can
      reconstruct turn-taking, barge-in, and filler timing.
"""

from __future__ import annotations

import logging
import sys
import time
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.processors import JSONRenderer, TimeStamper, format_exc_info
from structlog.stdlib import BoundLogger, LoggerFactory


# Per-call wall-clock origin. Set by `set_call_start_time(session_id)` from
# the WebSocket handler at "start" event. Used by `_add_call_relative_time`
# to stamp every subsequent log event with `t_ms_since_call_start`.
_call_start_epoch_s: ContextVar[float] = ContextVar(
    "_call_start_epoch_s", default=0.0
)
_session_id_var: ContextVar[str] = ContextVar("_session_id_var", default="")


def set_call_start_time(session_id: str) -> None:
    """
    Anchor the per-call clock at *now* for the current asyncio task chain.
    Subsequent log events from this task tree will include the elapsed
    `t_ms` since this anchor (DFS-007 instrumentation requirement).
    """
    _call_start_epoch_s.set(time.time())
    _session_id_var.set(session_id)


def get_call_elapsed_ms() -> float:
    """Return ms since the per-call clock was anchored, or 0 if unset."""
    start = _call_start_epoch_s.get()
    if start <= 0:
        return 0.0
    return (time.time() - start) * 1000.0


def _add_call_relative_time(_, __, event_dict):
    """structlog processor: stamp t_ms relative to call start."""
    start = _call_start_epoch_s.get()
    if start > 0:
        event_dict["t_ms"] = round((time.time() - start) * 1000.0, 1)
    sid = _session_id_var.get()
    if sid and "session_id" not in event_dict:
        event_dict["session_id"] = sid
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structured JSON logging with OpenTelemetry correlation.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # stdlib logging — raw messages only; structlog handles formatting.
    # `force=True` so we override any handlers uvicorn or others installed
    # before us; otherwise our INFO-level structured logs from named
    # loggers ("pipeline.production", "api.websocket") may flow through
    # an existing handler we did not configure for line-buffered stdout
    # and never reach Log Analytics. DFS-007 §6 instrumentation.
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )
    # Some libraries (notably uvicorn workers) attach their own handlers
    # to the root logger; ensure they propagate at INFO too.
    logging.getLogger().setLevel(level)

    # Silence noisy SDKs whose DEBUG output buries our structured events.
    # Azure Monitor / Core HTTP-policy logging dumps every request+response
    # header at DEBUG; keep at WARNING. Same for urllib3 and websockets.
    for noisy in (
        "azure",
        "azure.core.pipeline.policies.http_logging_policy",
        "azure.monitor.opentelemetry",
        "urllib3.connectionpool",
        "websockets.client",
        "websockets.server",
        "opentelemetry.attributes",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        # ms-precision UTC ISO8601 with "Z" suffix; DFS-007 §6 instrumentation.
        TimeStamper(fmt="%Y-%m-%dT%H:%M:%S.%fZ", utc=True),
        _add_call_relative_time,
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
    ]

    if log_level.upper() == "DEBUG":
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        processors = shared_processors + [
            format_exc_info,
            JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BoundLogger:
    """Get a structlog logger."""
    return structlog.get_logger(name)


# References
# [^SL1]: structlog authors. (2024). structlog: Structured Logging for Python.
#          https://www.structlog.org/  Separation of log emission from rendering.
# [^OT1]: OpenTelemetry. (2024). W3C Trace Context specification.
#          opentelemetry.io/docs/concepts/signals/traces/
# [^AM1]: Microsoft. (2024). Azure Monitor OpenTelemetry Distro.
#          learn.microsoft.com/azure/azure-monitor/app/opentelemetry-configuration
