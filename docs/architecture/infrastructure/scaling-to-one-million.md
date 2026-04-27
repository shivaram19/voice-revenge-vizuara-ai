# Infrastructure: Scaling to 1,000,000 Concurrent Sessions

**Version**: 1.0  
**Date**: 2026-04-25  
**Assumption**: Average session duration = 5 minutes; peak = 2× average.

---

## Capacity Planning

### Traffic Model
| Metric | Value |
|--------|-------|
| Target concurrent sessions | 1,000,000 |
| Average session duration | 300s |
| New sessions per second (avg) | 3,333 |
| New sessions per second (peak) | 6,666 |
| Audio bitrate | 32 kbps (Opus) |
| Total audio bandwidth | 32 Gbps |

---

## Layer-by-Layer Scaling

### 1. Edge / SFU Layer
**Function**: Route media packets.
**Bottleneck**: CPU (packet forwarding) and bandwidth.

**Capacity per node** (LiveKit SFU benchmark):
- ~10,000 concurrent subscribers per core
- ~1,000 publishers per core

**For 1M sessions** (assuming 1 publisher + 1 subscriber each):
- CPU cores needed: ~2,000
- Servers (64-core): ~32
- With 2× redundancy: **64 nodes**

**Scaling trigger**: Packet throughput per node > 80% capacity.

---

### 2. STT Service Layer
**Function**: Speech-to-text inference.
**Bottleneck**: GPU memory and compute.

**Capacity per GPU** (A10G, Distil-Whisper):
- ~50 concurrent streams per GPU (real-time factor 0.17×)
- With batching: ~80 streams

**For 1M sessions**:
- GPUs needed: 12,500
- Nodes (4 GPU each): ~3,125
- With 1.5× headroom: **~4,700 GPU nodes**

**Cost optimization**:
- Use CPU for 30% of streams (English, low-complexity audio): saves ~1,400 GPUs.
- Use spot instances for non-peak: saves 60%.

---

### 3. LLM Service Layer
**Function**: Language model inference.
**Bottleneck**: GPU memory (KV cache) and token throughput.

**Capacity per GPU** (A10G, Qwen2.5-7B, vLLM):
- ~100 concurrent sessions at 20 tokens/s
- TTFT: ~200ms

**For 1M sessions**:
- GPUs needed: 10,000
- Nodes (4 GPU each): ~2,500
- With 1.5× headroom: **~3,750 GPU nodes**

**Optimization**: Continuous batching (vLLM PagedAttention) increases throughput 3-5× over naive batching.

**Citation**: Kwon et al. (2023), SOSP [^25].

---

### 4. TTS Service Layer
**Function**: Text-to-speech synthesis.
**Bottleneck**: CPU compute (Piper) or GPU memory (Coqui).

**Capacity per CPU core** (Piper, x86):
- ~20 concurrent streams

**For 1M sessions**:
- Cores needed: 50,000
- Nodes (64-core): ~781
- With 1.5× headroom: **~1,200 CPU nodes**

**Optimization**: GPU-accelerated TTS (Orpheus via vLLM) reduces node count 10× but increases GPU load.

---

### 5. Memory / Vector DB Layer
**Function**: RAG retrieval and conversation history.
**Bottleneck**: Vector search latency and memory.

**Architecture**: Sharded Qdrant cluster with FAISS edge caches.

**Per-shard capacity** (Qdrant):
- ~10,000 QPS per node
- 1M sessions × 1 query/turn × 10 turns/session = 10M queries/session lifetime
- Active QPS during peak: ~100,000

**Nodes needed**: ~10 Qdrant shards + 3× replication = **30 nodes**

**Optimization**: VoiceAgentRAG semantic cache reduces Qdrant load by 75% [^14].

---

### 6. Orchestration / Control Plane
**Function**: Agent state machines, session management.
**Bottleneck**: State store latency.

**Architecture**:
- **Redis Cluster**: Working memory (session state, turn buffers).
- **Kafka**: Event bus for cross-service communication.
- **PostgreSQL**: Persistent conversation history.

**Redis capacity**: 1M sessions × 10KB state = 10GB. Sharded across 10 nodes.

---

## Total Infrastructure Footprint

| Layer | Nodes | Type | Monthly Cost (on-demand) |
|-------|-------|------|--------------------------|
| SFU | 64 | 64-core CPU | $200K |
| STT | 4,700 | 4×GPU (A10G) | $4.7M |
| LLM | 3,750 | 4×GPU (A10G) | $3.75M |
| TTS | 1,200 | 64-core CPU | $300K |
| Vector DB | 30 | 16-core CPU | $30K |
| Redis/Kafka | 20 | 16-core CPU | $20K |
| **Total** | **~9,800** | — | **~$9M/month** |

**With optimizations** (spot, MIG, CPU fallback):
- **Reduced cost**: ~$3-4M/month
- **Per-minute cost**: $3M / (1M × 60 × 24 × 30) ≈ **$0.0007/minute**

---

## Geographic Distribution

For global latency < 100ms:
- **US-East**: 30% of capacity
- **US-West**: 20%
- **EU-West**: 25%
- **APAC**: 20%
- **LATAM**: 5%

**Data residency**: EU sessions stay in EU (GDPR). Enterprise customers receive dedicated regions on contract.

---

## Observability at Scale

### Metrics Pipeline
```
Service ──► Prometheus ──► Thanos ──► Grafana
              │
              └──► AlertManager ──► PagerDuty
```

### Key SLIs
| SLI | Target | Measurement |
|-----|--------|-------------|
| Turn-gap P95 | <500ms | Time from speech end to first audio byte |
| STT WER | <5% | Per-session sampled evaluation |
| TTS MOS | >3.5 | Weekly human evaluation batch |
| System availability | 99.99% | Uptime excluding planned maintenance |
| Cost per minute | <$0.005 | TCO / total minutes served |

---

## References
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^25]: Kwon, W., et al. (2023). vLLM: Efficient Memory Management for Large Language Model Serving with PagedAttention. *SOSP*.
[^25]: Kwon, W., et al. (2023). vLLM: Efficient Memory Management for Large Language Model Serving with PagedAttention. *SOSP*.

[^1]: Kwon, W., et al. (2023). vLLM: Efficient Memory Management for Large Language Model Serving with PagedAttention. *SOSP*.
[^2]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
