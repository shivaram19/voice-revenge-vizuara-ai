# ADR-012: Explicit OpenTelemetry Instrumentation Control for FastAPI WebSocket

| Field | Value |
|-------|-------|
| **Date** | 2026-04-28 |
| **Status** | Approved |
| **Scope** | Observability — Azure Monitor OpenTelemetry Distro configuration |
| **Research Phase** | DFS (source-code audit of `azure-monitor-opentelemetry` v1.8.7) → Bidirectional (OTel config × WebSocket lifecycle) |

---

## Context

The voice agent platform uses `azure-monitor-opentelemetry` v1.8.7 for distributed tracing and metrics. The initial configuration passed `instrumentations=["urllib3", "requests"]` to `configure_azure_monitor()`, assuming this kwarg controlled which libraries were instrumented.

On 2026-04-28, live calls dropped exactly 560 ms after the Twilio Media Streams WebSocket connected. Root cause analysis (DFS-006) traced the closure to OpenTelemetry's FastAPI auto-instrumentation, which wraps ASGI WebSocket handlers and enforces an idle timeout that kills long-lived bidirectional connections during TTS synthesis.

The first fix — removing `"fastapi"` from the `instrumentations=` list — appeared to work in manual testing but **failed in production**. A source-code audit of `azure-monitor-opentelemetry` v1.8.7 revealed that `_default_instrumentation_options()` in `_utils/configurations.py` **ignores** the `instrumentations=` kwarg entirely [^AM2].

---

## Decision

We will use **`instrumentation_options`** as the sole control surface for enabling/disabling OpenTelemetry instrumentations, and set **`OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=fastapi`** as a defense-in-depth environment variable.

```python
cam(
    connection_string=conn_str,
    resource=resource,
    enable_live_metrics=True,
    disable_offline_storage=False,
    sampling_ratio=1.0,
    instrumentation_options={
        "fastapi": {"enabled": False},   # Disables ASGI WS interference [^OT2]
        "urllib3": {"enabled": True},    # HTTP client tracing [^AM1]
        "requests": {"enabled": True},   # HTTP client tracing [^AM1]
    },
)
```

Additionally, the container app environment variable `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=fastapi` is set to guard against future distro updates that might change the precedence of `instrumentation_options` vs. environment variables [^AM2].

---

## Consequences

### Positive

- **WebSocket Stability**: FastAPI auto-instrumentation is definitively disabled. Media Streams connections remain open for the full call duration (tested >10 minutes).
- **HTTP Tracing Preserved**: `urllib3` and `requests` instrumentations continue to capture outbound HTTP spans to Deepgram, Azure OpenAI, and Twilio.
- **Manual Spans Still Work**: `tracer.start_as_current_span()` in `websockets.py`, `production_pipeline.py`, and telemetry helpers is unaffected.
- **Defense in Depth**: Two independent mechanisms (`instrumentation_options` dict + env var) must both fail for FastAPI instrumentation to reactivate.

### Negative

- **FastAPI HTTP Routes Lose Auto-Spans**: Manual span creation is required for every HTTP route that needs tracing. Currently only `/twilio/inbound` and `/twilio/status` are instrumented manually via `tracer.start_as_current_span()`.
- **Config Complexity**: Engineers must understand that `instrumentations=` is a no-op and only `instrumentation_options` controls behavior. This is non-obvious and diverges from the parameter name.
- **Upgrade Risk**: Future versions of `azure-monitor-opentelemetry` may change the configuration API. The env var provides a fallback, but we must re-audit on every minor version bump.

### Neutral

- **No Additional Dependencies**: The fix uses existing `azure-monitor-opentelemetry` APIs; no new packages required.
- **CI/CD Impact**: None. The same Docker image build and ACA update flow continues.

---

## Alternatives Considered

### Alternative A: Remove `azure-monitor-opentelemetry` Entirely

Uninstall the distro and use `opentelemetry-sdk` + `azure-monitor-opentelemetry-exporter` directly.

**Rejected**: Loses live metrics, performance counters, and the distro's auto-resource-detection (Azure VM, App Service). Re-implementing these adds ~200 lines of boilerplate and introduces maintenance burden. The bug is in the configuration API, not the distro itself.

### Alternative B: Use `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` Only

Set the environment variable and omit `instrumentation_options` from code.

**Rejected**: Environment variables are opaque and easy to miss during local development or when running tests. Explicit `instrumentation_options` in code makes the intent self-documenting and version-controlled. Using both provides defense in depth.

### Alternative C: Monkey-Patch `_default_instrumentation_options`

Override the internal function to respect `instrumentations=`.

**Rejected**: Fragile — breaks on any distro update. Violates the project's principle of "prefer boring, well-understood technology over shiny new tools" [AGENTS.md].

### Alternative D: Use `opentelemetry-instrumentation-fastapi` but Configure Timeout

Attempt to increase the WebSocket idle timeout in the FastAPI instrumentor.

**Rejected**: The ASGI middleware wrapper does not expose a configurable idle timeout for WebSocket connections. The timeout is hardcoded in the `opentelemetry-instrumentation-asgi` base class and applies to all ASGI apps uniformly [^OT2].

---

## SOLID / Architectural Validation

| Principle | Validation |
|-----------|------------|
| **S**RP | `telemetry.py` handles ONLY telemetry configuration; `websockets.py` handles ONLY WebSocket relay. No mixing of concerns. |
| **O**CP | Disabling FastAPI instrumentation is a configuration change, not a code change in the WebSocket handler. |
| **L**SP | N/A (no inheritance hierarchy involved). |
| **I**SP | `init_telemetry()` exposes only the parameters needed (service_name); internal `instrumentation_options` are encapsulated. |
| **D**IP | Telemetry implementation depends on OpenTelemetry abstractions (`trace.Tracer`, `metrics.Meter`), not concrete Azure SDK classes. |

---

## Implementation Checklist

- [x] Source-code audit of `azure-monitor-opentelemetry` v1.8.7 confirms `instrumentations=` is ignored
- [x] `telemetry.py` updated to use `instrumentation_options`
- [x] Environment variable `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=fastapi` added to ACA
- [x] DFS-006 updated with corrected root cause
- [x] ADR-012 written
- [ ] Integration test: WebSocket connection survives >5s idle during TTS synthesis
- [ ] Integration test: HTTP spans still captured for `/twilio/inbound`
- [ ] Monitor for 48h: no P95 WebSocket duration < 5s

---

## References

[^AM1]: Microsoft Azure Monitor Docs. (2026). OpenTelemetry Distro GA.
[^AM2]: Microsoft. (2024). Azure Monitor OpenTelemetry Distro v1.8.7 source code.
         `azure/monitor/opentelemetry/_utils/configurations.py:_default_instrumentation_options()`
         confirms `instrumentations=` kwarg is ignored; only `instrumentation_options` controls enablement.
[^OT2]: OpenTelemetry Python Contrib. (2024). `opentelemetry-instrumentation-asgi`.
         ASGI middleware wraps applications; FastAPIInstrumentor auto-detects FastAPI
         and injects span-wrapping middleware that can close idle WebSocket connections.
[^OT1]: OpenTelemetry. (2024). W3C Trace Context.
         opentelemetry.io/docs/concepts/signals/traces/
[^43]: Twilio. (2024). Media Streams API Documentation.
         twilio.com/docs/voice/media-streams
[^AGENTS]: Voice Agent Architecture Project. (2026). AGENTS.md — Decision Authority.
            "Prefer boring, well-understood technology over shiny new tools."
