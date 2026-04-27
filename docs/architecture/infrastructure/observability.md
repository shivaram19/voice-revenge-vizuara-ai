# Observability: RED, USE, and Voice-Specific Metrics

**Version**: 1.0  
**Date**: 2026-04-25  
**Ref**: Google SRE Book (Beyer et al., 2016); Dapper (Sigelman et al., 2010)

---

## RED Metrics (Per Service)

### STT Service
| Metric | Type | Target | Alert Threshold |
|--------|------|--------|-----------------|
| `stt_rate` | Counter | — | — |
| `stt_errors_total` | Counter | <0.1% | >1% |
| `stt_duration_seconds` | Histogram | P50<200ms, P95<400ms | P95>500ms |
| `stt_wer` | Gauge | <5% | >8% |

### LLM Service
| Metric | Type | Target | Alert Threshold |
|--------|------|--------|-----------------|
| `llm_ttft_seconds` | Histogram | P50<200ms, P95<400ms | P95>600ms |
| `llm_tokens_per_second` | Gauge | >20 | <10 |
| `llm_tool_call_errors` | Counter | <0.5% | >2% |

### TTS Service
| Metric | Type | Target | Alert Threshold |
|--------|------|--------|-----------------|
| `tts_ttfb_seconds` | Histogram | P50<100ms, P95<200ms | P95>300ms |
| `tts_rtf` | Gauge | <0.5× | >1.0× |

### Transport / SFU
| Metric | Type | Target | Alert Threshold |
|--------|------|--------|-----------------|
| `sfu_packet_loss` | Gauge | <0.1% | >1% |
| `sfu_jitter_ms` | Gauge | <20ms | >50ms |

---

## USE Metrics (Per Resource)

### GPU
| Metric | Type | Target | Alert Threshold |
|--------|------|--------|-----------------|
| `gpu_utilization` | Gauge | 60-80% | >95% or <10% |
| `gpu_memory_used` | Gauge | <80% | >95% |
| `gpu_temperature` | Gauge | <80°C | >85°C |

### CPU
| Metric | Type | Target | Alert Threshold |
|--------|------|--------|-----------------|
| `cpu_utilization` | Gauge | 60-80% | >90% |
| `cpu_load_average` | Gauge | <cores×0.7 | >cores |

---

## Voice-Specific Metrics

### Turn-Gap Latency
**Definition**: Time from VAD `speech_end` to first TTS audio byte received by client.
```
turn_gap = tts_first_byte_timestamp - vad_speech_end_timestamp
```
**Target**: P95 < 500ms  
**Measurement**: Distributed tracing (OpenTelemetry) across STT→LLM→TTS pipeline.

### Barge-In Response Time
**Definition**: Time from VAD `speech_start` (during agent speaking) to TTS stream abort.
**Target**: P95 < 50ms  
**Measurement**: Agent Controller internal timer.

### Conversation Quality Score
**Definition**: Composite of:
- ASR WER (sampled)
- User interruption rate (too many interruptions = poor turn-taking)
- Session completion rate
- Post-call survey (if available)

**Target**: >4.0/5.0  
**Measurement**: Weekly batch evaluation on 1% of sessions.

---

## Distributed Tracing

**Trace Structure** (OpenTelemetry):
```
Session: session_id="abc-123"
├── Span: VAD (5ms)
├── Span: STT (250ms)
│   └── Span: Model Inference (200ms)
├── Span: Memory Retrieval (5ms)
│   └── Span: FAISS Cache (0.5ms)
├── Span: LLM Generation (400ms)
│   └── Span: TTFT (150ms)
│   └── Span: Token Generation (250ms)
├── Span: TTS Synthesis (180ms)
│   └── Span: TTFB (80ms)
└── Span: Network Delivery (30ms)
```

**Critical Path Highlighting**: The longest sequential span chain determines turn-gap. In the example above: VAD→STT inference→LLM TTFT→TTS TTFB→Network = 200+150+80+30 = 460ms.

---

## Dashboards

### SRE Dashboard (Grafana)
- Global: Concurrent sessions, turn-gap P50/P95, error rate, cost/hour.
- Per-region: Latency heatmap, packet loss, GPU utilization.
- Per-service: RED metrics, top 10 slowest traces.

### Product Dashboard
- Daily active sessions, average session duration, user satisfaction.
- Most common intents, tool usage rates, fallback rates.
- Cost per session, revenue per session (if applicable).

---

## Alerting Rules (Prometheus AlertManager)

```yaml
groups:
  - name: voice-agent
    rules:
      - alert: HighTurnGapLatency
        expr: histogram_quantile(0.95, turn_gap_seconds) > 0.5
        for: 5m
        annotations:
          summary: "P95 turn-gap exceeds 500ms"
          
      - alert: STTHighErrorRate
        expr: rate(stt_errors_total[5m]) / rate(stt_rate[5m]) > 0.01
        for: 3m
        annotations:
          summary: "STT error rate > 1%"
          
      - alert: GPUOverheating
        expr: gpu_temperature > 85
        for: 2m
        annotations:
          summary: "GPU temperature critical"

---

## References
[^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
[^29]: Beyer, C., et al. (2016). Site Reliability Engineering: How Google Runs Production Systems. O'Reilly.
[^52]: Sigelman, B. H., et al. (2010). Dapper, a Large-Scale Distributed Systems Tracing Infrastructure. Google Technical Report.
[^53]: OpenTelemetry. (2023). OpenTelemetry Specification. opentelemetry.io.
[^54]: Wilkes, J. (2020). Google-Wide Cluster Scheduling: The Next Generation. Google SRE Book, Chapter 24.

[^1]: Beyer, C., et al. (2016). Site Reliability Engineering: How Google Runs Production Systems. O'Reilly.
[^2]: Sigelman, B. H., et al. (2010). Dapper, a Large-Scale Distributed Systems Tracing Infrastructure. Google Technical Report.
[^3]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.
[^4]: OpenTelemetry. (2023). OpenTelemetry Specification. opentelemetry.io.
[^5]: Wilkes, J. (2020). Google-Wide Cluster Scheduling: The Next Generation. Google SRE Book, Chapter 24.
```
