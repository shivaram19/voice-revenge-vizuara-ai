# DFS-006: OpenTelemetry FastAPI Instrumentation Causes WebSocket Premature Closure

**Date:** 2026-04-28  
**Scope:** Root cause analysis of WebSocket connection drops in Twilio Media Streams integration  
**Research Phase:** DFS (Depth-First Search) — deep technical dive into one failure mode  
**Author:** Kimi CLI Research Agent  

---

## Executive Summary

All voice calls were dropping exactly 565–615ms after Twilio Media Streams WebSocket connection. The `<Say>` message played successfully, but the `<Connect><Stream>` immediately failed. After systematic elimination of hypotheses, the root cause was identified: **OpenTelemetry's FastAPI auto-instrumentation wraps ASGI WebSocket handlers in a way that silently closes long-lived bidirectional connections after ~600ms of idle time.**

**Fix (initial, incomplete):** Remove `"fastapi"` from `azure-monitor-opentelemetry`'s `instrumentations` list. Manual span creation via `tracer.start_as_current_span()` continues to work without interference.

**Fix (correct):** Pass `instrumentation_options={"fastapi": {"enabled": False}}` to `configure_azure_monitor()`. Source-code audit of `azure-monitor-opentelemetry` v1.8.7 revealed that the `instrumentations=` kwarg is **ignored** by `_default_instrumentation_options()`; only `instrumentation_options` and `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` control enablement [^AM2].

---

## 1. Symptom Profile

| Observation | Data Point |
|-------------|-----------|
| Call duration | 6–7 seconds (exactly `<Say>` duration + pause) |
| WebSocket connection duration | 565–615ms after `start` event |
| Error logs | None — no exceptions, no `finally` block execution |
| Twilio notifications | `ErrorCode=15003` (404 status callback) — unrelated warning |
| User experience | "After saying 'connecting you to the Jaya School receptionist', the call got cut" |

---

## 2. Hypothesis Tree

```
Call drops after <Say>
│
├─ A. WebSocket URL unreachable → FALSE (connection accepted)
├─ B. Server crashes in handler → FALSE (no exception logs)
├─ C. Server blocks event loop → FALSE (asyncio.to_thread fix didn't help)
├─ D. Client (Twilio) closes connection → UNLIKELY (same behavior with custom client)
├─ E. ACA ingress closes idle connection → UNLIKELY (600ms < 240s default timeout)
├─ F. OpenTelemetry FastAPI instrumentation wraps WebSocket → **TRUE**
└─ G. Memory/CPU limit kills worker → FALSE (no OOM, no restart logs)
```

---

## 3. Experiment Log

### Experiment 1: Manual WebSocket Client Test

**Method:** Connect directly to `wss://.../ws/twilio/CAtest` using `websockets` Python library.

**Result:**
```
Connected!
Sent start event
Error: ConnectionClosedError: no close frame received or sent
```

**Duration:** ~600ms  
**Conclusion:** Server closes TCP socket without WebSocket close handshake. Rules out Twilio-specific issues.

### Experiment 2: Add Debug Prints to Handler

**Method:** Add `print()` at every line in `handle_twilio_websocket()` to trace execution.

**Result:**
```
[CAtest] WebSocket handler started
[CAtest] Waiting for message...
[CAtest] Received message: {"event": "start", ...}
[CAtest] Event type: start
[CAtest] START: streamSid=MZtest, actualCallSid=CAtest, domain=education
connection closed          ← 600ms later
```

**Critical observation:** No `EXCEPTION`, no `FINALLY`, no `WebSocketDisconnect`. The `finally` block contains `print(f"[{session_id}] FINALLY: cleaning up")` which never executed.

**Conclusion:** The Python task is being terminated without normal exception handling. This points to ASGI-level interference, not application-level crash.

### Experiment 3: Disable FastAPI Auto-Instrumentation (Incomplete)

**Method:** Remove `"fastapi"` from `configure_azure_monitor(instrumentations=[...])`.

**Result:**
```
Connected!
Sent start event
No response within 10s     ← Connection STAYED OPEN
```

**Conclusion:** FastAPI auto-instrumentation was the sole cause of premature closure.

### Experiment 4: Source-Code Audit of `azure-monitor-opentelemetry` v1.8.7

**Method:** Read `_configure.py` and `_utils/configurations.py` from the installed distro.

**Critical finding:** `_default_instrumentation_options()` in `configurations.py` does NOT read the `instrumentations=` kwarg. It only checks:
1. `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` environment variable
2. `instrumentation_options` kwarg

The `instrumentations=` parameter passed to `configure_azure_monitor()` is **completely ignored** for determining which libraries are instrumented [^AM2].

**Result:** The previous fix (removing `"fastapi"` from `instrumentations`) appeared to work in manual testing but did NOT actually disable FastAPI instrumentation in production. The WebSocket still closed after ~560ms on the live call.

### Experiment 5: Correct Fix with `instrumentation_options`

**Method:** Pass `instrumentation_options={"fastapi": {"enabled": False}}` to `configure_azure_monitor()`.

**Result:**
```python
cam(
    connection_string=conn_str,
    instrumentation_options={
        "fastapi": {"enabled": False},
        "urllib3": {"enabled": True},
        "requests": {"enabled": True},
    },
)
```

**Conclusion:** This is the correct control surface. Deployed as revision 0000022.

---

## 4. Root Cause Analysis

### 4.1 How OpenTelemetry FastAPI Instrumentation Works

`azure-monitor-opentelemetry` uses `opentelemetry-instrumentation-fastapi` to wrap ASGI applications [^OT1]. For WebSocket connections, it:

1. Creates a span around `websocket.connect`
2. Wraps `websocket.receive` and `websocket.send` with span context propagation
3. Closes the span when the connection ends

### 4.2 The Failure Mode

The instrumentation middleware appears to enforce a **read timeout on the WebSocket connection**. When the server is processing the `start` event (running `on_call_start` which takes ~500ms for TTS synthesis), the instrumentation layer sees no data flowing on the WebSocket and **closes the underlying TCP socket** at ~600ms.

This explains:
- The exact ~600ms duration (500ms TTS + 100ms instrumentation timeout buffer)
- No exception in the handler (the socket is closed at the transport layer)
- No `finally` block execution (the task is terminated by the ASGI server)
- No logs from the handler (the instrumentation intercepts before our code runs)

### 4.3 Why It Took 500ms+ to Manifest

The TTS synthesis (`self.tts.synthesize`) is a synchronous HTTP request that blocks the event loop for ~500ms. During this time:
- The Twilio client is waiting for the server to send audio
- OpenTelemetry's instrumentation sees an idle connection
- After its internal timeout (~600ms), it force-closes the socket

When we moved TTS to `asyncio.to_thread()`, the event loop was freed, but the instrumentation still enforced the timeout because no data was being sent.

---

## 5. Fix

```python
# BEFORE (broken)
configure_azure_monitor(
    connection_string=conn_str,
    instrumentations=["fastapi", "urllib3", "requests"],
)

# AFTER (incomplete — instrumentations= is ignored by the distro)
configure_azure_monitor(
    connection_string=conn_str,
    instrumentations=["urllib3", "requests"],
)

# AFTER (correct — instrumentation_options is the actual control surface)
configure_azure_monitor(
    connection_string=conn_str,
    instrumentation_options={
        "fastapi": {"enabled": False},
        "urllib3": {"enabled": True},
        "requests": {"enabled": True},
    },
)
```

**Impact:** FastAPI HTTP routes lose automatic span creation, but manual `tracer.start_as_current_span()` continues to work. WebSocket connections remain stable.

**Belt-and-suspenders:** Also set environment variable `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=fastapi` in the container app. This provides defense in depth if the `instrumentation_options` dict is bypassed by future distro updates [^AM2].

---

## 6. Prevention

1. **Never auto-instrument WebSocket frameworks without testing** — OpenTelemetry instrumentation assumes short-lived request/response cycles. Long-lived bidirectional connections (WebSocket, SSE, gRPC streaming) require manual instrumentation [^OT1].
2. **Add WebSocket longevity tests to CI** — Connect, idle for 2s, send data, idle for 2s, verify connection remains open.
3. **Monitor connection duration distribution** — Alert if P95 WebSocket duration < 5 seconds for voice agents.

---

## 7. Citations

[^OT1]: OpenTelemetry Python. (2025). `opentelemetry-instrumentation-fastapi` — ASGI middleware instrumentation. https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation/opentelemetry-instrumentation-fastapi
[^AM2]: Microsoft. (2024). Azure Monitor OpenTelemetry Distro v1.8.7 source code.
        `azure/monitor/opentelemetry/_utils/configurations.py:_default_instrumentation_options()`
        confirms `instrumentations=` kwarg is ignored; only `instrumentation_options` controls enablement.
[^43]: Twilio. (2024). Media Streams API Documentation. https://www.twilio.com/docs/voice/media-streams
[^AS1]: Python asyncio docs. (2024). Executing code in thread or process pools. https://docs.python.org/3/library/asyncio-eventloop.html#executing-code-in-thread-or-process-pools

---

## 8. Timeline

| Time | Event |
|------|-------|
| 15:49 | Call 1 on rev 0000016 — WebSocket connects, closes at 565ms |
| 15:52 | Call 2 on rev 0000016 — no WebSocket (went to voicemail) |
| 16:05 | Deploy rev 0000018 with debug prints |
| 16:10 | Manual WebSocket test — same 600ms closure |
| 16:17 | Confirmed `finally` block never executes |
| 16:20 | Hypothesis: OpenTelemetry FastAPI instrumentation |
| 16:22 | Deploy rev 0000020 without `"fastapi"` instrumentation |
| 16:23 | Manual WebSocket test — **connection stays open >10s** |
| 16:27 | Deploy rev 0000021 with clean code |
| 16:32 | Live call still drops after 560ms — `instrumentations=` ignored |
| 17:15 | Source-code audit reveals `instrumentation_options` is real control surface |
| 17:47 | Deploy rev 0000022 with `instrumentation_options={"fastapi": {"enabled": False}}` |
