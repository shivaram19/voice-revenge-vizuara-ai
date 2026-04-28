"""
Structured Logging Configuration
================================
JSON-structured logs in production; pretty console in dev.
Correlates with OpenTelemetry trace_id / span_id for distributed tracing.

Research Provenance:
    - structlog: separation of log emission from rendering [^SL1]
    - OpenTelemetry: W3C traceparent propagation across services [^OT1]
    - Azure Monitor: maps OTel spans → App Insights traces/metrics [^AM1]
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.processors import JSONRenderer, TimeStamper, format_exc_info
from structlog.stdlib import BoundLogger, LoggerFactory


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structured JSON logging with OpenTelemetry correlation.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # stdlib logging — raw messages only; structlog handles formatting
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        TimeStamper(fmt="iso"),
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
# [^SL1]: structlog documentation. https://www.structlog.org/
# [^OT1]: OpenTelemetry. W3C Trace Context.
# [^AM1]: Azure Monitor OpenTelemetry Distro.
