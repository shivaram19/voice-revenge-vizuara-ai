"""
Latency Tracker — Per-Component Instrumentation
===============================================
Measures and reports P50/P90/P95 latency for each pipeline stage.
Research: TeamDay AI (2026) recommends component-level tracking to
identify bottlenecks [^31]; Hamming AI sets P95 > 800ms as warning [^34].

Ref: prometheus_client for metrics exposition.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""
    name: str
    samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    count: int = 0
    total_ms: float = 0.0

    def record(self, duration_ms: float) -> None:
        self.samples.append(duration_ms)
        self.count += 1
        self.total_ms += duration_ms

    @property
    def p50(self) -> float:
        return self._percentile(0.50)

    @property
    def p90(self) -> float:
        return self._percentile(0.90)

    @property
    def p95(self) -> float:
        return self._percentile(0.95)

    @property
    def mean(self) -> float:
        return self.total_ms / max(self.count, 1)

    def _percentile(self, q: float) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        idx = int(len(s) * q)
        idx = min(idx, len(s) - 1)
        return s[idx]


class LatencyTracker:
    """
    Tracks latency across pipeline stages.

    Usage:
        tracker = LatencyTracker()
        with tracker.measure("stt"):
            transcript = stt.transcribe(audio)
        print(tracker.report())
    """

    def __init__(self):
        self._stages: Dict[str, StageMetrics] = {}
        self._active: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, stage: str) -> None:
        """Mark the start of a stage."""
        self._active[stage] = time.perf_counter()

    def end(self, stage: str) -> None:
        """Mark the end of a stage and record the duration."""
        if stage not in self._active:
            return
        elapsed = (time.perf_counter() - self._active[stage]) * 1000.0
        self._get_stage(stage).record(elapsed)
        del self._active[stage]

    def measure(self, stage: str):
        """Context manager for measuring a stage."""
        return _MeasureContext(self, stage)

    def record(self, stage: str, duration_ms: float) -> None:
        """Manually record a duration."""
        self._get_stage(stage).record(duration_ms)

    def report(self) -> Dict[str, Dict[str, float]]:
        """Return a dict of stage → {p50, p90, p95, mean, count}."""
        return {
            name: {
                "p50": m.p50,
                "p90": m.p90,
                "p95": m.p95,
                "mean": m.mean,
                "count": m.count,
            }
            for name, m in self._stages.items()
        }

    def print_report(self, prefix: str = "") -> None:
        """Pretty-print latency report."""
        print(f"\n{prefix}Latency Report:")
        for name, metrics in self._stages.items():
            print(
                f"  {name:12s}  count={metrics.count:4d}  "
                f"mean={metrics.mean:6.1f}ms  p50={metrics.p50:6.1f}ms  "
                f"p90={metrics.p90:6.1f}ms  p95={metrics.p95:6.1f}ms"
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_stage(self, name: str) -> StageMetrics:
        if name not in self._stages:
            self._stages[name] = StageMetrics(name=name)
        return self._stages[name]


class _MeasureContext:
    """Context manager helper for LatencyTracker.measure()."""

    def __init__(self, tracker: LatencyTracker, stage: str):
        self.tracker = tracker
        self.stage = stage

    def __enter__(self):
        self.tracker.start(self.stage)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tracker.end(self.stage)
        return False


# References
# [^31]: TeamDay AI. (2026). Voice AI Architecture Guide.
# [^34]: Introl. (2026). Voice AI Infrastructure.
