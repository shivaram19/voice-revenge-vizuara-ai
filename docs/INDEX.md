# Documentation Index & Navigation Graph

This file maps the documentation topology for rapid traversal.

---

## By Research Phase

### BFS (Breadth-First Landscape)
| Document | Domains Covered | Key Insight |
|----------|----------------|-------------|
| [BFS-01](research/bfs/01-voice-ai-landscape.md) | All 8 modules | Dependency graph of curriculum |

### DFS (Depth-First Deep Dives)
| Document | Technology | Key Finding |
|----------|-----------|-------------|
| [DFS-01](research/dfs/01-whisper-deep-dive.md) | Whisper family | Distil-Whisper is Pareto-optimal for English |
| [DFS-02](research/dfs/02-transport-protocols-webrtc-vs-websocket.md) | WebRTC/WebSocket | WebRTC for client, gRPC for internal |
| [DFS-03](research/dfs/03-vad-endpointing-deep-dive.md) | VAD | Silero VAD is production sweet spot |
| [DFS-04](research/dfs/04-tts-engine-analysis.md) | TTS engines | Piper for edge, Coqui XTTS for quality |
| [DFS-05](research/dfs/05-llm-tool-use-agentic-workflows.md) | LLM/Agents | Function calling default; ReAct for complex |

### Bidirectional Analysis
| Document | Cross-Domain Map | Key Insight |
|----------|-----------------|-------------|
| [BIDIR-01](research/bidirectional/01-latency-architecture-co-design.md) | Latency ↔ Architecture | Latency inverts standard software patterns |
| [BIDIR-02](research/bidirectional/02-cost-quality-scaling-triangle.md) | Cost ↔ Quality ↔ Scale | Self-hosted 20× cheaper at scale |

---

## By Decision Record

| ADR | Decision | Status | Primary Citation |
|-----|----------|--------|------------------|
| [ADR-001](adrs/ADR-001-transport-protocol.md) | WebRTC for client transport | Accepted | LiveKit 2026, UGent thesis |
| [ADR-002](adrs/ADR-002-asr-model-selection.md) | Distil-Whisper tiered strategy | Accepted | Gandhi et al. 2023 |
| [ADR-003](adrs/ADR-003-memory-retrieval-strategy.md) | VoiceAgentRAG dual-agent | Accepted | Qiu et al. 2026 |

---

## By Architecture Layer

| Layer | Document | Interface File |
|-------|----------|----------------|
| Overview | [architecture/overview.md](architecture/overview.md) | — |
| State Machine | [architecture/data-flow/conversation-state-machine.md](architecture/data-flow/conversation-state-machine.md) | — |
| Scaling | [architecture/infrastructure/scaling-to-one-million.md](architecture/infrastructure/scaling-to-one-million.md) | — |
| Config | — | [src/infrastructure/config.py](../src/infrastructure/config.py) |
| Interfaces | — | [src/infrastructure/interfaces.py](../src/infrastructure/interfaces.py) |

---

## By Principle

| Document | Personas | Application |
|----------|----------|-------------|
| [principles/design-principles.md](principles/design-principles.md) | All 10 | Filter for every decision |
| [engine-thoughts/interpretation-engine.md](engine-thoughts/interpretation-engine.md) | Meta-cognitive | How research is synthesized |

---

## By Bibliography

[references/bibliography.md](references/bibliography.md) — 39 canonical sources.

---

## Traversal Pathways

**"I want to understand the full landscape"** → BFS-01 → BIDIR-01 → BIDIR-02

**"I want to know why we chose X"** → ADR-### → DFS-## → Bibliography entry

**"I want to build a component"** → Architecture Overview → Interfaces → Config → DFS deep-dive

**"I want to understand the research methodology"** → Engine Thoughts → Principles → BFS/DFS

**"I want to scale to 1M users"** → Scaling doc → ADR-002 → BIDIR-02 → Infrastructure

---

*Index version: 1.0*  
*Last updated: 2026-04-25*
