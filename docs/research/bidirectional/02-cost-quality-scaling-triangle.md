# BIDIR-02: The Cost-Quality-Scaling Triangle

**Research Phase**: Bidirectional economic analysis  
**Scope**: How cost constraints force quality and scaling trade-offs  
**Date**: 2026-04-25

---

## The Impossibility Triangle

In voice AI infrastructure, you can optimize for at most two of:
1. **Low cost** ($0.01/minute)
2. **High quality** (human-like, low WER)
3. **Massive scale** (1M concurrent sessions)

This document maps the Pareto frontier with citations.

---

## Cost Breakdown at Scale

### Per-Minute Cost Model

| Component | Low-Cost Path | High-Quality Path | Unit Cost |
|-----------|--------------|-------------------|-----------|
| ASR | Distil-Whisper (CPU) | Deepgram Nova-3 API | $0.00 vs $0.006/min |
| LLM | Llama 3.1 8B (self-hosted) | GPT-4o API | $0.0005 vs $0.01/min |
| TTS | Piper (CPU) | ElevenLabs Flash | $0.00 vs $0.005/min |
| Infrastructure | Spot CPU instances | Dedicated GPU cluster | $0.05 vs $0.50/hr/stream |

**Low-cost total**: ~$0.01/minute  
**High-quality total**: ~$0.05/minute  
**Delta**: 5×

**Citation**: Chanl.ai (2026) production cost analysis [^19]; Inworld.ai GPU cloud comparison [^63].

---

## Scaling Economics

### The GPU Bottleneck

At 1,000 concurrent sessions with GPU-based ASR + LLM + TTS:
- **ASR**: Distil-Whisper on A10G handles ~50 streams/GPU → 20 GPUs
- **LLM**: vLLM Qwen2.5-7B on A10G handles ~100 streams/GPU → 10 GPUs
- **TTS**: Piper on CPU handles ~20 streams/core → 50 CPU cores

**Total infrastructure**: ~30 GPU nodes + 50 CPU cores ≈ $150/hr  
**Per-minute cost**: $150 / (1000 × 60) = $0.0025/min  
**With cloud APIs**: 1000 × $0.05/min = $50/min = $3000/hr

**Self-hosted is 20× cheaper at scale** — but requires engineering investment.

**Citation**: NVIDIA (2023) Riva autoscaling guide [^31]; Barroso et al. (2018) [^30].

---

## Quality Degradation Curves

### ASR: WER vs Cost
```
WER (%)
  10│
    │     ● Cloud API (Deepgram)
   5│    /
    │   /  ● Distil-Whisper
   3│  /  /
    │ /  /   ● Whisper large-v3
   1│/  /
    └──────────────────────────→ Cost ($/min)
      Low     Medium    High
```

### TTS: MOS vs Cost
```
MOS
   5│          ● ElevenLabs
    │         /
   4│        ● Coqui XTTS
    │       /
   3│      ● Piper
    │     /
   2│    /
    └──────────────────────────→ Cost ($/min)
```

**Insight**: The steepest quality gains are in the "medium" cost band. Diminishing returns above that.

---

## Tiered Deployment Strategy

To serve 1M users without bankruptcy, use **tiered quality**:

| Tier | Users | ASR | LLM | TTS | Target |
|------|-------|-----|-----|-----|--------|
| Free | 80% | Distil-Whisper CPU | Llama 3.1 8B | Piper | Functional |
| Pro | 18% | faster-whisper GPU | GPT-4o-mini | Coqui VITS | Good |
| Enterprise | 2% | Whisper large-v3 | GPT-4o | ElevenLabs | Excellent |

**This mirrors CDN strategies**: serve static content from edge (cheap), dynamic from origin (expensive).

---

## Scaling Patterns

### Pattern 1: Horizontal Pod Autoscaling (HPA)
Scale GPU pods based on custom metrics (queue depth, TTFT).

**Implementation**: Prometheus → Prometheus Adapter → HPA  
**Metric**: `nv_inference_queue_duration_us`  
**Target**: Average queue time < 500ms per pod

**Citation**: NVIDIA (2023) [^31]; Kubernetes HPA v2 documentation.

### Pattern 2: GPU Multi-Instance (MIG)
On A100/H100, partition GPU into 7 instances. Each instance runs one model type.

**Efficiency gain**: 3-4× utilization vs whole-GPU allocation.

### Pattern 3: Spot/Preemptible Fallback
Run batch jobs (post-call analytics, model fine-tuning) on spot instances.

**Cost savings**: 60-70%.

**Risk**: Job interruption. Mitigation: checkpoint every 5 minutes.

**Citation**: Callsphere.tech (2026) [^64].

---

## The Altruism Dimension

Cost optimization is not just profit — it is **accessibility**.

- A voice agent costing $0.05/min is unaffordable for developing markets.
- A voice agent costing $0.005/min can serve billions.

**Open-source stack** (Piper + Distil-Whisper + Llama) achieves this. The research responsibility is to make this stack production-grade, not just demo-quality.

---

## References
[^19]: Chanl.ai. (2026). Voice Agent Platform Architecture.
[^30]: Barroso, L. A., et al. (2018). *The Datacenter as a Computer*.
[^31]: NVIDIA. (2023). Autoscaling Riva with Kubernetes.
[^63]: Inworld.ai. (2026). Best GPU Cloud for AI Inference.
[^64]: Callsphere.tech. (2026). AI Agent Deployment on Kubernetes.

[^1]: Chanl.ai. (2026). Voice Agent Platform Architecture.
[^2]: Inworld.ai. (2026). Best GPU Cloud for AI Inference.
[^3]: NVIDIA. (2023). Autoscaling Riva with Kubernetes.
[^4]: Barroso, L. A., et al. (2018). *The Datacenter as a Computer*.
[^5]: Callsphere.tech. (2026). AI Agent Deployment on Kubernetes.
