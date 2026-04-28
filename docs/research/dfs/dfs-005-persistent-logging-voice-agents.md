# DFS-005: Persistent Logging for Voice Agents — Depth-First Analysis

**Date:** 2026-04-28  
**Scope:** Azure Application Insights integration, structured logging, PII redaction, and cost optimization for voice agent observability  
**Research Phase:** DFS (Depth-First Search) — deep technical implementation guide  
**Author:** Kimi CLI Research Agent  

---

## Executive Summary

Azure Container Apps provides only ~100 lines of ephemeral console logs. For a production voice agent handling real customer calls, this is unacceptable — transcripts, latency metrics, and error traces are lost on every container restart. This DFS implements a complete OpenTelemetry → Application Insights logging pipeline with PII redaction, structured JSON logs, and cost-conscious retention policies.

**Key decisions:**
- Use `azure-monitor-opentelemetry` (GA, feature parity with Classic SDK) [^AM1]
- Redact PII at source: Deepgram `redact=pci,ssn,numbers` + custom phone redaction [^27]
- Structured JSON logs via `structlog` with trace/span correlation
- Per-table retention: 30 days for traces, 90 days for exceptions

---

## 1. Technology Selection

### 1.1 `azure-monitor-opentelemetry` vs `opencensus-ext-azure`

| Aspect | `azure-monitor-opentelemetry` | `opencensus-ext-azure` |
|--------|------------------------------|------------------------|
| **Status** | **Recommended (GA)** | Legacy / maintenance mode |
| **Architecture** | OpenTelemetry-native distro | Classic Application Insights SDK |
| **Future** | Active development | Frozen — no new features |
| **Auto-instrumentation** | FastAPI, Django, Flask, requests, psycopg2 | Limited |

> *"Updated FAQ guidance to recommend starting with OpenTelemetry now that the Azure Monitor OpenTelemetry Distro has reached feature parity with the Classic API SDK."* — Microsoft Azure Monitor Docs, February 2026 [^AM1]

### 1.2 Installation

```bash
pip install azure-monitor-opentelemetry opentelemetry-instrumentation-fastapi
```

---

## 2. Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Voice Agent    │────►│  OpenTelemetry   │────►│  Azure Monitor  │
│  (FastAPI +     │     │  SDK (spans,     │     │  (Application   │
│   WebSocket)    │     │   metrics, logs) │     │   Insights)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │                           │
                              ▼                           ▼
                        ┌──────────────┐           ┌──────────────┐
                        │  structlog   │           │  Log Analytics│
                        │  (JSON)      │           │  workspace    │
                        └──────────────┘           └──────────────┘
```

---

## 3. Implementation

### 3.1 Telemetry Initialization (`src/infrastructure/telemetry.py`)

```python
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace, metrics

configure_azure_monitor(
    connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    enable_live_metrics=True,
    instrumentations=["fastapi", "urllib3", "requests"],
)
```

### 3.2 Per-Call Trace Correlation

Every Twilio call gets a root span with `call.session_id` = CallSid:

```python
with tracer.start_as_current_span("voice.call") as span:
    span.set_attribute("call.session_id", call_sid)
    # All STT, LLM, TTS events within this call share trace_id
```

**KQL query to view a complete call:**

```kusto
traces
| where customDimensions["call.session_id"] == "CA123456..."
| project timestamp, message, customDimensions
| order by timestamp asc
```

### 3.3 Structured Log Schema

| Event Name | Level | Required Fields | Optional Fields |
|-----------|-------|----------------|-----------------|
| `call.started` | INFO | `session_id`, `from_number`, `to_number`, `domain` | `custom_parameters` |
| `call.ended` | INFO | `session_id`, `duration_sec`, `turn_count` | `hangup_reason` |
| `stt.transcript` | INFO | `session_id`, `is_final`, `confidence` | `transcript_length` |
| `stt.barge_in` | INFO | `session_id` | `recovery_ms` |
| `llm.response` | INFO | `session_id`, `model`, `latency_ms` | `response_length` |
| `tts.synthesis` | INFO | `session_id`, `voice_model`, `latency_ms` | `text_length` |
| `pipeline.error` | ERROR | `session_id`, `error_type` | `stack_trace`, `stage` |

### 3.4 Custom Metrics

| Metric Name | Type | Description |
|------------|------|-------------|
| `voice.calls.total` | Counter | Total calls handled |
| `voice.turns.total` | Counter | Total conversation turns |
| `voice.latency.ms` | Histogram | Stage latency (LLM, TTS) |
| `voice.barge_in.total` | Counter | Barge-in events |

---

## 4. PII Redaction

### 4.1 Defense in Depth

| Layer | What | Implementation |
|-------|------|----------------|
| 1. STT API | Transcription | Deepgram `redact=pci,ssn,numbers` [^27] |
| 2. Logs | Phone numbers | Custom `redact_phone()` → `***-0290` |
| 3. Transcripts | Text PII | `redact_text()` → `[PHONE]`, `[EMAIL]` |
| 4. Traces | Span attributes | Never store raw transcripts in span attributes |

### 4.2 Deepgram PII Redaction

```python
stt_config = StreamingSTTConfig(
    # ... other params ...
    redact="pci,ssn,numbers",  # 90%+ accuracy [^27]
)
```

### 4.3 Phone Number Redaction

```python
def redact_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 10:
        return f"***-{digits[-4:]}"
    return "[REDACTED]"
```

---

## 5. Azure Container Apps Configuration

### 5.1 Environment Variables

```bash
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...;IngestionEndpoint=...
LOG_LEVEL=INFO
DEPLOYMENT_ENV=production
APP_VERSION=0.1.0
```

### 5.2 Diagnostic Settings (Bicep)

```bicep
resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'voice-agent-logs'
  scope: containerApp
  properties: {
    logs: [
      {
        category: 'ContainerAppConsoleLogs'
        enabled: true
        retentionPolicy: { days: 30, enabled: true }
      }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
    workspaceId: logAnalyticsWorkspace.id
  }
}
```

### 5.3 Cost Optimization

| Strategy | Impact |
|----------|--------|
| Set per-table retention | Keep exceptions 90d, traces 30d |
| OpenTelemetry sampling | 100% for low-volume voice calls (ok) |
| Filter at source | Never log PCM buffers or audio payloads |
| Use Basic Logs for verbose stdout | ~80% cheaper, 8-day retention |

**Estimated cost:** ~$2.30/GB ingested/month. A voice agent with 100 calls/day (~10 min each) generates ~500MB logs/month = **~$1.15/month**.

---

## 6. Dashboard Queries (KQL)

### 6.1 Call Volume Per Hour

```kusto
customEvents
| where name == "call.started"
| summarize count() by bin(timestamp, 1h)
| render timechart
```

### 6.2 Average Turn Latency

```kusto
customMetrics
| where name == "voice.latency.ms"
| summarize avg(value), percentile(value, 95) by bin(timestamp, 1h), customDimensions.stage
| render timechart
```

### 6.3 Barge-In Frequency

```kusto
customEvents
| where name == "stt.barge_in"
| summarize count() by bin(timestamp, 1h)
| render timechart
```

### 6.4 Error Rate by Stage

```kusto
traces
| where customDimensions["call.event"] == "pipeline.error"
| summarize count() by bin(timestamp, 5m), customDimensions["error.context.stage"]
```

---

## 7. Research Citations

[^AM1]: Microsoft Azure Monitor Docs. (2026). OpenTelemetry Distro GA.
[^HM1]: Hamming AI. (2026). Monitor Pipecat Agents in Production. https://hamming.ai/resources/monitor-pipecat-agents-production-logging-tracing-alerts
[^OT1]: OpenTelemetry. W3C Trace Context.
[^SL1]: structlog documentation. https://www.structlog.org/
[^27]: Deepgram. (2026). PII Redaction Developer Guide. https://deepgram.com/learn/pii-redaction-developer-guide-speech-api-setup
[^26]: Hamming AI. (2026). PII Redaction for Voice Agents. https://hamming.ai/resources/pii-redaction-voice-agents

---

## 8. Implementation Checklist

- [x] `azure-monitor-opentelemetry` dependency added to `pyproject.toml`
- [x] `src/infrastructure/telemetry.py` — telemetry client + custom metrics
- [x] `src/infrastructure/logging_config.py` — structlog JSON configuration
- [x] `src/infrastructure/pii_redaction.py` — phone/email/SSN redaction
- [x] `src/api/lifespan.py` — telemetry initialization at startup
- [x] `src/api/websockets.py` — structured logging + span correlation
- [x] `src/streaming/streaming_stt_deepgram.py` — Deepgram PII redaction param
- [x] `src/infrastructure/production_pipeline.py` — all pipeline events logged
- [ ] `APPLICATIONINSIGHTS_CONNECTION_STRING` added to ACA environment variables
- [ ] Diagnostic settings configured in Azure Portal / Bicep
- [ ] KQL dashboard created in Application Insights
- [ ] Alert rules: error rate >1%, P95 LLM latency >3000ms
