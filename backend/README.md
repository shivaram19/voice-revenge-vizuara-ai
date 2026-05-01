# Voice Agent Architecture: Research-Driven Engineering

> **Built for engineers who want to go deep.**
> Every decision is recited with its research provenance. Every module is designed for million-user scale. Every abstraction is questioned from first principles.

---

## Documentation Topology

This repository is organized as a **cognitive map** — not a flat wiki, but a navigable knowledge graph where breadth, depth, and cross-connectivity are first-class dimensions.

```
docs/
├── research/
│   ├── bfs/              # Breadth-First Search: Landscape mapping across all domains
│   ├── dfs/              # Depth-First Search: Deep-dive into critical technologies
│   └── bidirectional/    # Bidirectional analysis: Cross-domain impact mapping
├── adrs/                 # Architecture Decision Records (ADR) — one per decision
├── architecture/
│   ├── components/       # Component definitions and interfaces
│   ├── data-flow/        # Streaming, event, and control flows
│   └── infrastructure/   # Deployment, scaling, and observability
├── principles/           # Design principles and personas
├── references/           # Canonical bibliography
└── engine-thoughts/      # Interpretation engine — how the research is perceived & synthesized
```

---

## Operating Personas

I operate simultaneously across these dimensions. Every architectural decision is filtered through all ten lenses:

| # | Persona | Mandate |
|---|---------|---------|
| 1 | **Research Scientist** | Every decision cites peer-reviewed source |
| 2 | **First-Principles Engineer** | Strip hype; rebuild from axioms (information theory, queueing theory, CAP theorem) |
| 3 | **Distributed Systems Architect** | Design for 1M+ concurrent users from Day 0 |
| 4 | **Infrastructure-First SRE** | Observability (RED/USE metrics) is not an afterthought |
| 5 | **Ethical Technologist** | Privacy by design, accessibility, energy efficiency |
| 6 | **Resource Strategist** | TCO and carbon cost before GPU vs CPU |
| 7 | **Diagnostic Problem-Solver** | Root-cause analysis using Dagum's Law and critical path tracing |
| 8 | **Curious Explorer** | Maintain lab notebook of experiments |
| 9 | **Clarity-Driven Communicator** | ADRs accompany every choice; complexity is the enemy |
| 10 | **Inner-Self Guided Builder** | Build what is *right*, not what is *easy* |

---

## Research Methodology

### BFS (Breadth-First Search)
Systematic landscape mapping across 8 curriculum modules:
- Voice Agent Architecture & Pipeline Design
- Speech-to-Text (ASR) Foundations
- Text-to-Speech (TTS) & Voice Output
- LLMs as the Brain
- Tool Use, Memory & Agentic Workflows
- Real-Time Streaming Voice Agents
- Production-Grade Architecture
- End-to-End Capstone Projects

### DFS (Depth-First Search)
Vertical deep-dives into bottleneck technologies:
- Whisper variants (Whisper, faster-whisper, Distil-Whisper, whisper.cpp)
- TTS engines (Piper, Coqui/VITS, Orpheus, Kokoro)
- Transport protocols (WebRTC vs WebSocket vs gRPC)
- VAD & endpointing (Silero, semantic VAD)
- Memory & RAG (VoiceAgentRAG, FAISS, Qdrant)

### Bidirectional Analysis
Cross-domain impact mapping:
- **ASR ↔ TTS**: Model selection on one side constrains latency budget on the other
- **Latency ↔ Cost**: Sub-500ms conversational latency requires GPU; CPU fallback saves 60-70% cost
- **Infrastructure ↔ Model Selection**: Kubernetes GPU autoscaling determines batch vs streaming ASR strategy
- **Memory ↔ Streaming**: RAG retrieval latency (50-300ms) can consume entire conversational budget

---

## Reading Pathways

**If you are a systems architect:** Start with `docs/architecture/overview.md`, then `docs/adrs/`.

**If you are a researcher:** Start with `docs/research/bfs/` for landscape, then `docs/research/dfs/` for depth.

**If you want to understand *why* decisions were made:** Read `docs/engine-thoughts/interpretation-engine.md`, then `docs/adrs/`.

**If you want the bibliography:** See `docs/references/bibliography.md`.

---

## Principle of Citation

> *"In God we trust; all others must bring data."* — W. Edwards Deming

Every claim, every latency figure, every architectural choice is tethered to its source. If a citation is missing, the claim is marked `[CITATION NEEDED]` and treated as hypothesis, not fact.

---

*Last updated: 2026-04-25*
*Research cycle: BFS-DFS-Bidirectional Phase I Complete*

---

## Fullstack Scaffold (Backend + Next.js Frontend)

The repository now includes:
- FastAPI backend routes for Voice CRM scaffold data at `/api/v1/crm/*`
- Next.js frontend workspace in `../frontend/` consuming backend APIs

### Quick Start

Backend:
- `python -m venv .venv`
- Windows: `.venv\Scripts\activate`
- `pip install -e .`
- `uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload`

Frontend (new terminal):
- `cd ../frontend`
- `npm install`
- `npm run dev`

Open `http://localhost:3000`.

### Manual Testing Guide

Use `docs/deployment/manual-testing-fullstack.md` for end-to-end manual validation steps.
