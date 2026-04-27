# ADR-003: Memory & Retrieval Strategy for Real-Time Conversations

## Status
**Accepted** — 2026-04-25

## Context
Voice agents require memory for context across turns. Standard RAG adds 50-300ms retrieval latency — consuming the entire conversational latency budget. We need a retrieval strategy compatible with sub-200ms response targets.

## Decision
**Implement a dual-agent memory router inspired by VoiceAgentRAG [^1]:**

1. **Semantic Cache (foreground)**: FAISS in-memory index for sub-millisecond lookups.
2. **Slow Thinker (background)**: Async agent that pre-fetches follow-up topics during the current response, using LLM topic prediction with 75% cache hit rate [^14].
3. **Vector Store (fallback)**: Qdrant or Pinecone for cold-start and cache misses.

## Architecture

```
User Utterance
     │
     ▼
┌─────────────────┐
│  Memory Router  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
Fast Talker  Slow Thinker
(foreground) (background)
    │         │
    ▼         ▼
Semantic    Vector Store
Cache       (Qdrant)
(FAISS)     │
    │       │
    └───┬───┘
        │
        ▼
   Context for LLM
```

## Consequences

### Positive
- **316× retrieval speedup** on cache hits (110ms → 0.35ms) [^14].
- **75% overall cache hit rate**, 79% on warm turns [^14].
- **Decouples retrieval from response generation**: retrieval happens during user listening time.
- **Compounding effect**: cache warms rapidly over first few turns.

### Negative
- **Memory overhead**: FAISS index holds top-k chunks per predicted topic.
- **Prediction accuracy**: LLM topic prediction adds token cost (~500 tokens/turn).
- **Cold start**: First query on a new topic requires full vector DB round-trip.

## Implementation Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Cache max size | 2000 chunks | Memory/speed trade-off |
| Cache TTL | 300s | Conversation topicality |
| Similarity threshold τ | 0.40 | FAISS precision tuning |
| Predictions per turn | 3-5 | Coverage vs cost balance |
| Prefetch top-k | 10 | Chunk diversity |
| Rate limit | 0.5s | Protect vector store |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Direct vector DB query | 50-300ms latency violates real-time constraint |
| GPTCache (reactive caching) | Only helps on repeated queries; voice conversations are sequential, not repetitive |
| Stream RAG | Predicts within single query lifecycle; doesn't exploit cross-turn predictability |
| No RAG (context-only) | LLM hallucinates on domain-specific knowledge; unacceptable for enterprise use |

## Research Provenance
- Qiu et al. (2026): "A typical vector database query adds 50–300ms to the response pipeline, which... pushes total latency well beyond the 200ms budget" [^14].
- Johnson et al. (2019): FAISS provides "efficient similarity search and clustering of dense vectors" [^36].
- Malkov & Yashunin (2016): HNSW indexing enables approximate nearest neighbor search with logarithmic complexity [^39].

## Revisit Trigger
Revisit if:
1. Vector DB edge caching reduces round-trip to <10ms (eliminates need for FAISS layer).
2. LLM context windows exceed 1M tokens, making full-document embedding viable without retrieval.
3. On-device embedding models achieve <50ms inference, enabling client-side retrieval.

## References
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^36]: Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE TBD*.
[^36]: Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE TBD*.
[^39]: Malkov, Y. A., & Yashunin, D. A. (2016). Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs. *arXiv:1603.09320*.
[^39]: Malkov, Y. A., & Yashunin, D. A. (2016). Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs. *arXiv:1603.09320*.

[^1]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^2]: Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE TBD*.
[^3]: Malkov, Y. A., & Yashunin, D. A. (2016). Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs. *arXiv:1603.09320*.
