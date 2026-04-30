# BFS-007: Voice Chunks RAG — Architectures for Cached + Retrieved Audio

> **Date:** 2026-04-30
> **Scope:** Breadth-first landscape mapping of architectures that retrieve / cache **voice audio chunks** for low-latency response in a real-time voice agent. Triggered by user directive to research voice-chunks RAG. Connects to the cached scenario flow already shipped (stage machine with summary/details/closing/backchannel pre-synth, commits `0268df3` + `36f6274`). Identifies which approaches deserve a DFS deep-dive.
> **Research Phase:** BFS — landscape mapping only.
> **Status:** Active. Drives a follow-up DFS-NN on the lead candidate.

---

## 1. Why this BFS exists

The current Jaya High School deployment uses a four-stage cached scenario flow: `summary`, `details`, `closing`, and `backchannel` audio bytes are pre-synthesised at call start in parallel and dispatched on keyword-match against the parent's transcript. The happy path is sub-50ms. The fallback path — when the parent's utterance does not match a stage's keyword set — is `LLM (~1s) + Bulbul TTS (~5–7s) + delivery`. That fallback is the next bottleneck.

This BFS asks: **what does the field do for the off-script case** — when the parent says something the stage machine doesn't anticipate, but a sensibly-chosen pre-recorded / pre-synthesised audio chunk would be the right reply? This is *voice-chunks RAG*: retrieve the right audio bytes from a corpus instead of generating them from scratch.

---

## 2. The five architectures in scope

Five distinct approaches surfaced in this scan. Each is a real design pattern with at least one published implementation.

### 2.1 Dual-Agent Predictive Cache (VoiceAgentRAG)

**Mechanism.** A "Slow Thinker" LLM runs in the background between agent turns, predicting 3–5 likely follow-up topics, retrieving relevant chunks from a vector DB, embedding them, and pre-populating an in-memory FAISS `IndexFlatIP` (cosine similarity). A "Fast Talker" foreground agent reads from this sub-millisecond cache to compose its reply; full retrieval only fires on cache miss [^Salesforce2026VoiceAgentRAG][^MarkTechPost2026].

**Reported numbers.** 75% overall cache hit rate; **316× retrieval speedup** (110ms → 0.35ms) on cache hits [^Salesforce2026VoiceAgentRAG]. Critical when the conversational budget is ~200ms total.

**Fit for our use case.** Strong. Predictive prefetch is exactly the gap our current stage-machine has — it can't anticipate questions like *"how much was last term?"*. A Slow Thinker could pre-fetch the answer to the top-N likely follow-ups.

**Concerns.** (i) Adds an LLM background-thread cost per call. (ii) FAISS embedding lookups on text, not audio — the *audio* still has to be synthesised at some point unless we maintain a parallel audio cache keyed by the same chunk IDs.

### 2.2 Speculative TTS

**Mechanism.** Generate likely response audio in advance based on context prediction; play immediately if the actual LLM reply matches; fall back to synthesis otherwise [^AIAgentsPlus2026][^Cresta2025].

**Reported numbers.** 30–40% cache hit rate from common-phrase hashing alone; 60% latency reduction on cached queries [^AIAgentsPlus2026].

**Fit.** Useful as a complement to 2.1 — speculative TTS is *audio* prediction; VoiceAgentRAG is *text/context* prediction. Our current cache_summary_ready in `_prepare_cached_scenario_audio` is essentially deterministic speculative TTS for the four stages.

**Concerns.** Mismatch detection is hard — if the LLM's actual phrasing diverges, you've wasted a synthesis. Works best for short common phrases (acknowledgments, fillers).

### 2.3 Hash-based phrase cache (no embedding)

**Mechanism.** Hash the LLM's intended-output text; look up in an LRU/key-value store of pre-synthesised audio bytes; play if hit, synthesise if miss [^Famulor2026].

**Reported numbers.** Cresta's report: 70–85% hit rate in production conversational apps with LRU [^Cresta2025]; sub-100ms p95 lookup [^MakeAI2025Pinecone].

**Fit.** Good for the predictable phrase population (greetings, "have a peaceful day", "Manchidi andi") that recurs across calls. Doesn't handle paraphrase — *"Have a nice day, sir"* and *"Have a peaceful day, sir"* are separate cache keys.

**Concerns.** Hit rate hits a ceiling once phrase variety exceeds the cached corpus. Doesn't help for novel parent utterances.

### 2.4 Embedding-similarity audio cache

**Mechanism.** Store pairs `(embedding(LLM_output_text), audio_bytes)` in a vector DB. When the LLM produces a new candidate response, embed it, search for nearest cached neighbour above a similarity threshold (commonly 0.95), and play cached audio if hit [^Pinecone2026][^DEV2025SemanticCache].

**Reported numbers.** Sub-millisecond search at million-vector scale [^Qdrant2026]; query latency p50 ≈ 45ms, p95 ≈ 120ms in production benchmarks [^Pinecone2026]. Threshold 0.95 catches paraphrases.

**Fit.** Strong for *recurring scenarios* across calls — the same Telugu blessing, the same "your fees are paid" confirmation. Across 100 calls, the corpus stabilises and hit rate climbs.

**Concerns.** Embedding model choice matters (multilingual or English-only? Telugu-aware?). Semantic threshold must be tuned per-domain. False positives play wrong audio.

### 2.5 Streaming TTS with sentence-level chunking

**Mechanism.** Stream LLM tokens; emit each completed sentence to TTS as it lands; play first sentence's audio while subsequent sentences are still being generated/synthesised [^LiveKit2025][^Cresta2025].

**Reported numbers.** First-audio under 300ms achievable end-to-end [^LiveKit2025]. Reduces *perceived* latency by 300–600ms even when total work is the same.

**Fit.** Orthogonal to caching — streaming reduces latency-to-first-audio when synthesis IS happening. Combine with 2.1–2.4: cache for the predictable path, stream for the unpredictable.

**Concerns.** Bulbul streaming support not yet validated in our deployment (DFS-010 §4 future work).

---

## 3. The vector DB layer (orthogonal substrate)

| DB | Strengths | Project status |
|---|---|---|
| **FAISS** (in-memory) | Fastest single-node lookup; simple API; the substrate VoiceAgentRAG's Fast Talker uses [^Salesforce2026VoiceAgentRAG] | Already in `pyproject.toml` (`faiss-cpu`) |
| **Qdrant** | Sub-ms search with persistence; Python SDK; runs locally / in Docker / cloud [^Qdrant2026] | Already in `pyproject.toml` (`qdrant-client`) |
| **Pinecone** | Managed simplicity; sub-100ms latency; hybrid search [^Pinecone2026] | Not provisioned |
| **Chroma / pgvector / Milvus** | Open-source alternatives | Not relevant given FAISS/Qdrant already pinned |

**Recommendation:** Use **FAISS in-memory for per-call hot cache** (matches VoiceAgentRAG's Fast Talker pattern, no infra change) and **Qdrant for cross-call persistent corpus** (already in deps; survives container restarts). Pinecone unnecessary given Qdrant coverage and the regional-data-jurisdiction concerns from BFS-006.

---

## 4. Comparison matrix

| Architecture | Hit rate | Cache lookup | Cross-call reuse | Off-script handling | New infra |
|---|---|---|---|---|---|
| 2.1 Dual-Agent (VoiceAgentRAG) | 75% [^Salesforce2026VoiceAgentRAG] | 0.35ms | yes (vector DB) | predictive prefetch | LLM-as-Slow-Thinker + FAISS |
| 2.2 Speculative TTS | 30–40% [^AIAgentsPlus2026] | <50ms | partial | none | minimal |
| 2.3 Hash cache | 70–85% [^Cresta2025] | <1ms | yes (key-value) | none | LRU map |
| 2.4 Embedding cache | tunable (threshold-dep.) | 50–120ms [^Pinecone2026] | yes (vector DB) | paraphrase-tolerant | embedding model + vector DB |
| 2.5 Streaming TTS | n/a (no cache) | n/a | n/a | reduces perceived latency | Bulbul streaming |

(Hit-rate columns are vendor-published; treat as directional. DFS-NN should reproduce on our actual corpus.)

---

## 5. Where our current implementation sits

The shipped cached-flow (`production_pipeline.py`, commits `0268df3` + `36f6274`) is a **deterministic-rule subset of 2.2 (Speculative TTS)**:

- Pre-synthesise per-call: yes
- Stage-keyword classifier: yes (5–17 keywords per stage)
- Cross-call audio reuse: **no** (cache flushed per session)
- Embedding similarity: **no**
- Off-script: **falls back to LLM+TTS** (~6s)

The natural next step is **2.1 (Dual-Agent) + 2.3 (cross-call hash cache)** — the combination that VoiceAgentRAG's authors used and reported 75% / 316× on. Embedding cache (2.4) and streaming (2.5) are useful refinements but not the highest-leverage next move.

---

## 6. BFS recommendation → DFS gate

**Promote to DFS:**

1. **VoiceAgentRAG dual-agent pattern** [^Salesforce2026VoiceAgentRAG]. The strongest Tier-1 evidence (arXiv preprint with reproducible benchmark). DFS would measure: actual per-turn classifier hit rate on the corpus from our 12+ test calls, FAISS index build time at session start, prediction quality of a Slow-Thinker LLM (likely Azure GPT-4o-mini at <500ms TTFT, already in our stack), and end-to-end first-audio latency on cache hit vs miss.
2. **Cross-call persistent audio corpus** in Qdrant (already in deps). Pre-synth a curated set of Telangana-register phrases (greetings, acknowledgments, common scenario fragments) once at deploy time; reuse across all calls and tenants. Reduces per-call cache-fill cost.

**Do not promote (yet):**

- Speculative TTS as a standalone — already partially implemented; useful only as a complement to the above.
- Embedding cache (2.4) — strictly more complex than hash cache for paraphrase tolerance we don't yet need; revisit after the dual-agent + hash cache lands.
- Streaming TTS (2.5) — useful regardless but blocked on Bulbul streaming support; track as a separate item.

---

## 7. Open questions for the DFS

1. **Slow Thinker model + cost.** Which LLM serves the Slow Thinker? Azure GPT-4o-mini is in our stack and has ~150ms TTFT; sufficient. Cost: 3–5 background calls per agent turn × call duration. TCO impact on a 60-second call?
2. **Audio cache key design.** Hash of `(scenario_id, intent, text)`? Or semantic-hash from embedding? Pure-text hashing is simpler but misses paraphrase.
3. **Audio storage.** Bytes in Redis (per-call) vs Qdrant payload (cross-call) vs Azure Blob (long-term). Redis already provisioned.
4. **Eviction policy.** LRU vs LFU vs scenario-locality. Cresta's 70–85% LRU number is on general-conversational apps; our intentional-call corpus may have a *different* recurrence shape.
5. **Cache-warming at deploy.** Pre-render the top-N expected phrases per scenario per language preference, push to Qdrant, ship as part of the image. Removes per-call cold-start cost.
6. **Privacy.** Audio bytes are not PII themselves but the *text* keys (parent name, child name) are. Cross-call corpus must redact before storage.

---

## 8. Trade-offs filtered through the 10-persona lens

| Persona | Verdict |
|---|---|
| Research Scientist | VoiceAgentRAG has Tier-1 arXiv source with reproducible benchmark. Hash + embedding caches grounded in cited industry production data. |
| First-Principles Engineer | "Don't generate what you can retrieve" is a primitive of distributed-systems engineering, not a voice-AI fad. |
| Distributed Systems Architect | Cross-call corpus + per-call hot cache scales linearly with tenants; FAISS-in-Container-App and Qdrant-as-shared-store both fit our existing topology. |
| Infrastructure-First SRE | Cache hit/miss + Slow-Thinker latency are first-class metrics; emit as structured events from the start. |
| Ethical Technologist | Pre-cached audio means consistent voice prosody across cache hits — UX consistency is a dignity property for the parent. |
| Resource Strategist | Cache hit rate × call duration directly maps to TTS+LLM cost saved. ROI calc fits in DFS. |
| Diagnostic Problem-Solver | Off-script LLM fallback is the current bottleneck (6s); voice-chunks RAG attacks it directly. |
| Curious Explorer | Streaming + cache hybrids and embedding-similarity refinements are explicitly listed as future work, not deferred to nowhere. |
| Clarity-Driven Communicator | This BFS + ADR-NN (next) capture the why and the choice. |
| Inner-Self Guided Builder | A parent who hears a *familiar warm phrase* at the right moment trusts the call. Cache enables this; LLM-only generation does not. |

---

## References

> Tiers per AGENTS.md: Tier 1 = peer-reviewed / arXiv-with-reproduction; Tier 2 = vendor docs / public-data; Tier 3 = industry blog (NOT normative).

### Tier 1 — Peer-reviewed / arXiv

[^Salesforce2026VoiceAgentRAG]: Salesforce AI Research. (2026). *VoiceAgentRAG: Solving the RAG Latency Bottleneck in Real-Time Voice Agents Using Dual-Agent Architectures.* arXiv:2603.02206. Published 2026-03; the dual-agent pattern + 75% / 316× benchmarks.

### Tier 2 — Vendor / official documentation

[^Pinecone2026]: Pinecone vector database documentation. pinecone.io — sub-100ms latency, hybrid search.
[^Qdrant2026]: Qdrant vs Pinecone — Vector Databases for AI Apps. qdrant.tech/blog/comparing-qdrant-vs-pinecone-vector-databases.
[^LiveKit2025]: LiveKit. *Voice Agent Architecture: STT, LLM, and TTS Pipelines Explained.* livekit.com/blog/voice-agent-architecture.
[^Cresta2025]: Cresta. *Engineering for Real-Time Voice Agent Latency.* cresta.com/blog/engineering-for-real-time-voice-agent-latency.

### Tier 3 — Industry coverage (NOT normative; landscape only)

[^MarkTechPost2026]: MarkTechPost. (2026-03-30). *Salesforce AI Research Releases VoiceAgentRAG: A Dual-Agent Memory Router that Cuts Voice RAG Retrieval Latency by 316x.* — coverage of [^Salesforce2026VoiceAgentRAG]; cited only to confirm the paper's existence and high-level claims.
[^AIAgentsPlus2026]: AI Agents Plus. *Voice AI Latency Optimization Techniques.* — speculative-TTS pattern reference.
[^Famulor2026]: Famulor. *Realtime vs Pipeline Voice Agent: Architecture Guide 2026.* — phrase-based caching context.
[^MakeAI2025Pinecone]: MakeAIHQ. *Vector Database Integration for ChatGPT Apps.* — sub-100ms-latency benchmark mention.
[^DEV2025SemanticCache]: dev.to/kuldeep_paul. *Reducing LLM Cost and Latency Using Semantic Caching.* — embedding similarity threshold reference.

### Implementation references

- Commits `0268df3` + `36f6274` — current cached scenario flow in production_pipeline.py.
- BFS-006 — Indian-name STT comparison (Sarvam jurisdictional argument carries here for vector DB choice).
- DFS-008 — Voice Intent Framework (the scenario contract this RAG layer would supplement).
- DFS-010 §5 Option B — Sarvam Bulbul integration (already shipped; relevant for streaming-TTS future work item §6 §5).
- pyproject.toml — `faiss-cpu` and `qdrant-client` already pinned.
