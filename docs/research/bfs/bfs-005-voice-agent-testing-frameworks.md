# BFS-005: Voice Agent Testing Frameworks — Breadth-First Landscape Mapping

**Date:** 2026-04-28  
**Scope:** Production testing, evaluation, and observability tools for real-time voice AI agents  
**Research Phase:** BFS (Breadth-First Search) — systematic coverage of the tooling landscape  
**Author:** Kimi CLI Research Agent  

---

## Executive Summary

Voice agent testing has evolved from manual call review to automated, metric-driven evaluation infrastructure. This BFS maps the full tooling landscape across eight major platforms, three testing methodologies (BFS/DFS/regression), and five observability layers. Key finding: **Hamming AI** offers the deepest voice-specific testing (50+ metrics, real PSTN calls, barge-in recovery), while **Braintrust** provides the most unified eval+observability platform.

---

## 1. Testing Framework Landscape

### 1.1 Hamming AI ⭐ Recommended for Production QA

| Attribute | Detail |
|-----------|--------|
| **URL** | https://hamming.ai |
| **Pricing** | ~$1,000–$3,000/mo (enterprise); contact sales |
| **Integration** | Low — native Vapi, Retell, LiveKit, Pipecat, Bland |
| **Depth** | ⭐⭐⭐⭐⭐ |

**Capabilities:**
- End-to-end call simulation via **real PSTN/SIP calls** (not API mocking)
- WebRTC testing for LiveKit with auto-provisioned rooms
- **50+ metrics**: latency (P50/P95/P99), turn control, barge-in stability, talk ratio, WER, hallucination scoring
- Scale testing: up to 1,000 concurrent synthetic sessions
- Regression gates in CI/CD
- Audio playback in traces — click any trace to hear actual conversation
- Heartbeat monitoring: scheduled synthetic calls detect outages before users report

**Latency thresholds:**
- P95 >800ms → warning
- P95 >1200ms → critical

**Barge-in testing:**
- Detects overlapping speech, measures barge-in recovery rate
- Validates context retention after interruption
- Target: >90% interruption recovery [^4]

### 1.2 Vapi Test Suites (Built-In)

| Attribute | Detail |
|-----------|--------|
| **Pricing** | Included with Vapi subscription; consumes calling minutes |
| **Integration** | Minimal for existing Vapi users |
| **Depth** | ⭐⭐☆☆☆ |

**Limitations:**
- AI-to-AI simulation only (no real PSTN)
- Transcript-only evaluation (misses audio quality, WER, latency)
- No background noise or interruption testing
- Max 15 min/test, 50 cases/suite, 250 runs max [^5][^7]

### 1.3 Retell AI QA / Evals

| Attribute | Detail |
|-----------|--------|
| **Pricing** | ~$0.04/min base + ~$0.10/min analyzed |
| **Integration** | Minimal (native to platform) |
| **Depth** | ⭐⭐⭐⭐☆ |

**Capabilities:**
- AI Quality Assurance against natural-language success criteria
- Weighted scoring (e.g., medical compliance 80%, booking 20%)
- Component-level latency breakdown (STT 210ms, LLM 380ms, TTS 124ms)
- Real-time alerts for transfer failures, function failures, success rate drops [^8][^9]

### 1.4 LiveKit Testing Helpers

| Attribute | Detail |
|-----------|--------|
| **Pricing** | Free (text-only) |
| **Integration** | Low — pytest / Vitest |
| **Depth** | ⭐☆☆☆☆ (text-only) |

**Critical Gap:** Text-only tests do NOT exercise the audio pipeline. Misses WebRTC timing, jitter, overlapping speech, network interference, and latency under production conditions [^11][^12].

### 1.5 Cekura

| Attribute | Detail |
|-----------|--------|
| **Pricing** | $30/mo dev (300 credits); enterprise custom |
| **Integration** | Low — Vapi, Retell, LiveKit native |
| **Depth** | ⭐⭐⭐⭐☆ |

- Production call simulation and monitoring
- 25+ predefined metrics (latency, interruptions, barge-in, consistency)
- Outcome evaluation: task completion, handoff rate, containment [^13][^14]

### 1.6 Future AGI Evals

| Attribute | Detail |
|-----------|--------|
| **Pricing** | Contact sales |
| **Integration** | Moderate — OpenTelemetry OTLP |
| **Depth** | ⭐⭐⭐⭐⭐ |

- Large-scale simulation (thousands of scenarios in minutes)
- Cross-provider reliability benchmarking
- TraceAI library: OpenTelemetry-based tracing with conversation-turn spans
- Agent Compass: pinpoints where and why quality dropped [^15][^16]

### 1.7 Braintrust

| Attribute | Detail |
|-----------|--------|
| **Pricing** | Free tier; paid from ~$249/mo |
| **Integration** | Low–moderate |
| **Depth** | ⭐⭐⭐⭐☆ |

- Unified eval + observability for voice, text, multimodal
- Audio attachments for debugging with actual audio playback
- Integration with Evalion for realistic simulation
- Custom scorers for voice-specific metrics [^17]

### 1.8 Roark

| Attribute | Detail |
|-----------|--------|
| **Pricing** | $500/mo (5,000 call minutes) |
| **Integration** | Low — one-click Vapi, Retell, LiveKit |
| **Depth** | ⭐⭐⭐⭐☆ |

- Production call replay testing
- 40+ built-in metrics including sentiment via Hume
- SOC2 and HIPAA compliant [^17]

---

## 2. Integration Complexity Matrix

| Tool | Best For | Pricing | Voice Depth | CI/CD Ready |
|------|----------|---------|-------------|-------------|
| Hamming AI | Production QA, scale, compliance | $1K–3K/mo | ⭐⭐⭐⭐⭐ | ✅ |
| Vapi Tests | Vapi users, sanity checks | Free w/ minutes | ⭐⭐☆☆☆ | ✅ |
| Retell QA | Retell users, analytics | ~$0.10/min | ⭐⭐⭐⭐☆ | ✅ |
| LiveKit | Fast unit tests, CI | Free | ⭐☆☆☆☆ | ✅ |
| Cekura | Cross-platform testing | $30/mo+ | ⭐⭐⭐⭐☆ | ✅ |
| Future AGI | Cross-provider benchmarking | Contact | ⭐⭐⭐⭐⭐ | ✅ |
| Braintrust | Unified eval (all modalities) | $249+/mo | ⭐⭐⭐⭐☆ | ✅ |
| Roark | Production replay, sentiment | $500/mo | ⭐⭐⭐⭐☆ | ✅ |

---

## 3. Key Research Citations

[^1]: Hamming AI. *Top Voice Agent Testing Platforms 2025*. https://hamming.ai/blog/voice-agent-testing-platforms-comparison-2025
[^4]: Hamming AI. *Voice Agent Evaluation Metrics*. https://hamming.ai/resources/voice-agent-evaluation-metrics-guide
[^5]: Vapi. *Voice Testing Documentation*. https://docs.vapi.ai/test/voice-testing
[^7]: Hamming AI. *How to Test Voice Agents Built with Vapi*. https://hamming.ai/blog/how-to-test-voice-agents-built-with-vapi
[^8]: Retell AI. *AI QA Metrics*. https://docs.retellai.com/ai-qa/terminologies
[^11]: LiveKit. *Testing and Evaluation*. https://docs.livekit.io/agents/start/testing/
[^13]: Cekura. *Pricing*. https://cekura.ai/pricing
[^15]: Future AGI. *Compare Voice AI Evaluation*. https://futureagi.com/blog/compare-voice-ai-evaluation-vapi-vs-future-agi/
[^17]: Braintrust. *Best Voice Agent Evaluation Tools 2025*. https://www.braintrust.dev/articles/best-voice-agent-evaluation-tools-2025

---

## 4. Recommendations for This Project

1. **Immediate (this sprint):** Implement OpenTelemetry tracing in pipeline → Application Insights. This gives us baseline observability without external cost.
2. **Short-term (next sprint):** Add Hamming AI synthetic calls for regression testing before each deployment. Budget ~$500/mo.
3. **Medium-term:** Build LLM-as-judge evaluation rubric for education-domain conversations (course accuracy, Dharmic tone adherence, barge-in recovery).
