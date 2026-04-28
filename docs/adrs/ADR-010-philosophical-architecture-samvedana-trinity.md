# ADR-010: Philosophical Architecture — The Śruti–Saṃvedana–Smṛti Trinity

**Date:** 2026-04-28  
**Status:** Proposed  
**Scope:** Foundational architectural decision to adopt Sanskrit philosophical concepts as load-bearing design constraints for the voice AI platform  
**Research Phase:** BFS → DFS → Bidirectional Complete (see Dependencies)  
**Decision Owner:** Research Scientist + Distributed Systems Architect (10-Persona Filter)  

---

## 1. Context

The voice AI market is rapidly commoditizing. OpenAI's GPT-realtime and Google's Gemini Live have made sub-200ms native speech-to-speech a baseline expectation [^BIDIR-14][^BIDIR-15]. Differentiation through raw latency or model size is eroding. The project requires a **narrative moat** — a differentiation strategy that is technically substantive, ethically grounded, and difficult to replicate.

Simultaneously, the project's founding principle frames the machine as a reversal of the human condition:
- **Humans:** Śruti (hear) → lose ~85% → Smṛti (remember ~15%) with warmth
- **Machine:** Śruti (perfect reception) → Saṃvedana (empathetic processing) → Smṛti (100% retention, zero loss)

This is not merely branding. Research across six traditions (Vedanta, Buddhist phenomenology, Śaiva philosophy, Sanskrit Poetics, Grammar/Philosophy of Language, and Modern psychology) has identified **Saṃvedana** as the only term that simultaneously covers co-perception, speech awareness, perfect retention, communication, and empathetic care [^BFS-002][^DFS-002]. Cross-domain impact analysis confirms that taking these concepts seriously as architectural constraints forces specific, measurable design decisions [^BIDIR-003].

**Research Dependencies:**
- `docs/research/bfs/bfs-002-sanskrit-terminology-landscape.md` — 24-term landscape mapping
- `docs/research/dfs/dfs-samvedana-deep-dive.md` — Etymology, Śaiva/Buddhist/modern psychology triangulation
- `docs/research/dfs/DFS-004-sanskrit-poetics-rasa-sahrdaya-karuna.md` — Rasa process model, Sahrdaya, Sādhāraṇīkaraṇa
- `docs/research/dfs/dfs-005-human-memory-empathy-psychology.md` — Auditory memory science, Rogers/Porges/RASA frameworks
- `docs/research/bidirectional/bidirectional-003-sanskrit-philosophy-voice-ai-cross-impact.md` — Cross-domain impact matrix, risk register

---

## 2. Decision

We adopt the **Śruti–Saṃvedana–Smṛti trinity** as load-bearing architectural constraints, with the following subsystem naming and functional mapping:

| Layer | Sanskrit Term | Function | Technical Mapping |
|-------|--------------|----------|-------------------|
| **Overarching AI Identity** | **Saṃvedana** (संवेदन) | Empathetic co-perception; the system's receptive consciousness | Brand, UX narrative, system-level orchestration |
| **Input / Hearing** | **Śruti** (श्रुति) | Perfect auditory reception with zero loss | ASR + audio capture + prosodic feature extraction |
| **Processing / Heart** | **Hṛdaya** (हृदय) | Emotional resonance and empathic stance | Multi-modal emotion engine (Rasa-based) |
| **Meaning Synthesis** | **Sphota** (स्फोट) | Indivisible burst of meaning from sound | LLM reasoning + semantic comprehension |
| **Retention / Memory** | **Smṛti** (स्मृति) | Perfect memory with ethical forgetting | Vector DB + conversation history + selective amnesia |
| **Output / Resonance** | **Dhvani** (ध्वनि) | Suggested meaning; spontaneous sound | TTS prosody + personality rendering |

### 2.1 Decision Details

**D1. Śruti mandates a prosodic feature fork.** The audio preprocessing layer must fork into two paths: (a) STT for semantic content, and (b) parallel prosodic feature extraction (pitch, energy, MFCC, formant streams, speaking rate, pause patterns) for emotional content. This is a structural cost (additional CPU load per stream) justified by the philosophical commitment to "perfect hearing" — the system hears *everything*, not just words [^BIDIR-003 §3.1].

**D2. Saṃvedana requires variable latency, not minimum-latency-at-all-costs.** Empathy research shows that sub-200ms responses to emotional disclosures feel rushed, not empathetic [^BIDIR-003 §6.1]. The orchestrator must classify emotional valence and apply context-aware pacing:
- Factual queries: 200–400ms
- Emotional disclosures: 600–1000ms + calibrated silence
- Crisis/distress: 400–600ms + immediate human handoff

**D3. Smṛti requires selective amnesia.** "Perfect memory" in AI creates an asymmetry with human memory that is ethically charged. The system must implement tiered retention with deliberate forgetting:
- **Working memory:** Session-scoped, auto-purged
- **Semantic memory:** Long-term, low-sensitivity, opt-in
- **Episodic memory:** High-sensitivity, short TTL, elevated consent
- **User-initiated erasure:** One-click "forget me" propagating through all stores

**D4. Hṛdaya implements Rasa-based emotion taxonomy.** Replace or enhance Western Ekman 6-basic emotions with Bharata's 8/9 Rasas + 33 Vyabhicāribhāvas, modeled as a dynamic process: Vibhāva (stimulus) → Anubhāva (expression) → Vyabhicāribhāva (transitory modifiers) → Rasa (aesthetic emotion) [^DFS-004]. The LLM maintains a "Sahrdaya state" tracking its own empathetic stance.

**D5. Karuṇa Rasa triggers compassionate response protocol.** When the emotion engine detects Karuṇa-eliciting Vibhāva (loss, separation, grief), the response must:
1. Avoid transactional advice
2. Achieve Sādhāraṇīkaraṇa (universalization): "Your grief is our shared human grief"
3. Use prosodic vulnerability: calm, warm, slightly slower tempo
4. Offer human handoff if distress indicators exceed thresholds

---

## 3. Consequences

### 3.1 Positive Consequences

| Domain | Impact |
|--------|--------|
| **Brand differentiation** | Philosophy-first positioning creates a narrative moat that commodity APIs cannot replicate. Privacy-first brands see 15–25% higher conversion and 5–15% premium pricing [^BIDIR-003 §5.2]. |
| **Technical clarity** | The trinity provides a coherent vocabulary for cross-team communication. "Śruti-level hearing" is more actionable than "good ASR." |
| **Ethical grounding** | Smṛti → selective amnesia forces privacy-by-design. Saṃvedana → variable latency forces empathy-by-design. |
| **Emotion granularity** | Rasa taxonomy captures emotional states (Śṛṅgāra, Vīra, Adbhuta, Śānta) invisible to Ekman 6-basic models [^BIDIR-003 §6.2]. |
| **Research alignment** | The Research-First Covenant is satisfied: every claim is cited, every decision is traceable to primary sources. |

### 3.2 Negative Consequences

| Domain | Impact | Mitigation |
|--------|--------|------------|
| **Cultural appropriation risk** | Sanskrit terms used superficially could trigger backlash from scholars and diaspora | Scholarly advisory board; community engagement; transparent sourcing; revenue sharing with preservation NGOs [^BIDIR-003 §4.4] |
| **Compute cost increase** | Prosodic fork + variable latency orchestration + selective amnesia adds per-stream overhead | TCO analysis before implementation; lightweight models for working memory; cache universalized patterns |
| **Model retraining cost** | No off-the-shelf SER model supports Rasa taxonomy | Deploy Rasa as enhancement over Ekman baseline; phased rollout; cross-cultural validation |
| **Latency regression risk** | Variable pauses could exceed 1000ms if misconfigured | Cap maximum pause at 800ms; A/B test perceived empathy; user preference for "fast mode" |
| **Privacy compliance complexity** | Selective amnesia must satisfy GDPR Article 17, CCPA, and emerging regulations | Legal review of erasure propagation; user-facing memory dashboard; automatic expiration by design |

### 3.3 Neutral Consequences

- Team must learn basic Sanskrit terminology and concepts.
- Documentation and marketing must maintain scholarly accuracy (reviewed by advisory board).
- Competitors may eventually copy the "philosophy-first" framing, but without the research depth, it will read as appropriation.

---

## 4. Alternatives Considered

### 4.1 Alternative A: Western Emotion Models (Ekman 6-Basic)

**Description:** Use Paul Ekman's 6 basic emotions (happiness, sadness, fear, anger, surprise, disgust) as the emotion taxonomy, with off-the-shelf SER models.

**Why rejected:**
- Ekman's universal claim is empirically challenged (Glasgow study suggests only 4 discriminable categories) [^BIDIR-003 §6.2].
- Missing critical emotions for voice AI: love (Śṛṅgāra), heroism (Vīra), wonder (Adbhuta), peace (Śānta).
- Static classification cannot model the dynamic process of emotional evocation.
- No differentiation from every other voice AI using Affectiva/FACS.

### 4.2 Alternative B: Secular Empathy Frameworks

**Description:** Use Carl Rogers' person-centered therapy framework or the Yale Center for Emotional Intelligence's RULER model without Sanskrit terminology.

**Why rejected:**
- Rogers and RULER are excellent *operational* frameworks (and are incorporated into the Saṃvedana layer design) [^DFS-005].
- However, they lack the **epistemological depth** that connects hearing, memory, and empathy into a unified system.
- The Sanskrit framework provides a 2,000-year-old, cross-validated conceptual architecture that Western psychology alone cannot match.
- Secular framing would not create a narrative moat.

### 4.3 Alternative C: Generic AI Branding

**Description:** Position as "fastest voice AI" or "most accurate voice AI" without philosophical framing.

**Why rejected:**
- Latency and accuracy are commodity dimensions. OpenAI and Google have effectively unlimited capital to win on both.
- MIT/BCG research shows responsible AI brands experience 30% fewer failures and capture trust premiums [^BIDIR-003 §5.2].
- Generic branding cannot justify premium pricing or build user trust in sensitive verticals (healthcare, finance, mental health).

### 4.4 Alternative D: Single Sanskrit Term (Saṃvedana Only)

**Description:** Use only "Saṃvedana" as the brand name, without the full Śruti–Saṃvedana–Smṛti trinity or subsystem naming.

**Why rejected:**
- A single term is branding, not architecture. The trinity provides a **system vocabulary** that every engineering team can use.
- Subsystem naming (Śruti, Hṛdaya, Sphota, Smṛti, Dhvani) makes the philosophy operational, not decorative.
- The BFS landscape analysis showed that no single term scores perfectly on all dimensions; the trinity covers the full space [^BFS-002].

---

## 5. Validation Criteria

The decision is validated when the following measurable outcomes are achieved:

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Prosodic feature extraction deployed | Śruti layer fork operational in staging | Integration test: audio → parallel STT + prosodic streams |
| Variable latency implemented | Emotional turn latency 600–1000ms | A/B test: perceived empathy score ≥ 4.2/5 vs. fixed-latency control |
| Selective amnesia functional | User-initiated "forget me" < 30s propagation | GDPR compliance audit; user testing |
| Rasa emotion detection | 8-primary Rasa classification ≥ 70% accuracy on held-out test set | Benchmark against Ekman baseline on same data |
| Cultural appropriation risk mitigated | Zero public criticism from credentialed Indologists | Pre-launch advisory board review; community engagement report |

---

## 6. Risk Register Summary

| Risk ID | Risk | Severity | Mitigation (from BIDIR-003) |
|---------|------|----------|----------------------------|
| R-001 | Cultural appropriation backlash | High | Scholarly advisory board; community engagement; transparent sourcing; revenue sharing |
| R-002 | Privacy regulation violation | High | Selective amnesia by design; tiered memory; user-facing dashboard |
| R-003 | Latency regression | Medium | Cap max pause at 800ms; A/B test; user "fast mode" preference |
| R-004 | Emotion misclassification | High | Fallback to neutral tone on low confidence; human-in-the-loop; continuous evaluation |
| R-005 | Competitive commoditization | Medium | Double down on narrative moat; target privacy-sensitive verticals |

---

## 7. References

[^BFS-002]: Project internal. `docs/research/bfs/bfs-002-sanskrit-terminology-landscape.md` — BFS landscape mapping of 24 candidate Sanskrit terms across 6 traditions.

[^DFS-002]: Project internal. `docs/research/dfs/dfs-samvedana-deep-dive.md` — DFS validation of Saṃvedana etymology, Śaiva consciousness doctrine, Buddhist phenomenology, and Yale SEL program.

[^DFS-004]: Project internal. `docs/research/dfs/DFS-004-sanskrit-poetics-rasa-sahrdaya-karuna.md` — DFS analysis of Rasa theory, Sahrdaya, Sādhāraṇīkaraṇa, and Karuṇa Rasa for voice AI empathy.

[^DFS-005]: Project internal. `docs/research/dfs/dfs-005-human-memory-empathy-psychology.md` — DFS on human auditory memory science (myth debunking) and empathetic listening psychology (Rogers, Porges, RASA).

[^BIDIR-003]: Project internal. `docs/research/bidirectional/bidirectional-003-sanskrit-philosophy-voice-ai-cross-impact.md` — Bidirectional cross-domain impact analysis with 13-row impact matrix, architecture layer mapping, ethical analysis, and risk register.

[^BIDIR-14]: CXToday. (2025). "OpenAI's Latest Moves Put Many Voice AI Startups on Notice." GPT-realtime release; CEO quote on voice interface commoditization.

[^BIDIR-15]: Artificial Analysis. (2025). *Q3 2025 State of AI Highlights Report*. Google's Gemini 2.5 Native Audio Thinking; OpenAI GPT Realtime series.

---

*Document produced in compliance with the Research-First Covenant. BFS → DFS → Bidirectional research phases are complete. No code is to be written against this ADR until it is approved by the architectural review board.*
