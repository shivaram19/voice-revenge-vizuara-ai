# ADR-020: Pronunciation Pipeline — VibeVoice + Sarvam Integration

**Date:** 2026-05-02  
**Status:** Proposed  
**Scope:** Architecture for teaching Sarvam Kavita correct Suryapet pronunciation using user-recorded reference audio  
**Decision Authority:** User directive 2026-05-02  

---

## Context

Sarvam Bulbul v3 speaker "kavitha" produces Telugu speech, but specific words ("matlardhanam", "ayipoyindhi", Suryapet proper nouns) are rendered with generic pan-Indian pronunciation rather than authentic Telangana rural register. The user — a native Suryapet speaker who attended Jaya High School — has volunteered to record reference pronunciations. The goal is to create a pipeline where:

1. User records words/phrases in authentic Suryapet register
2. The recordings are analyzed for phonetic/prosodic content
3. The extracted pronunciation knowledge is fed into Sarvam's TTS layer
4. Resulting audio is cached per-region for all future calls

## Decision

Implement a **three-tier pronunciation system**:

| Tier | Mechanism | Input | Output | Latency |
|---|---|---|---|---|
| **T1: Sarvam dict_id** | JSON word→replacement map | User-reviewed text mappings | Corrected text before synthesis | Zero (pre-processing) |
| **T2: VibeVoice acoustic analysis** | Extract acoustic tokens from user recordings | User's WAV recordings | Phonetic hints for dict refinement | Async (post-recording) |
| **T3: Sarvam enterprise clone** | Full speaker cloning | 30 min of user speech | Custom speaker ID replacing "kavitha" | API call |

T1 is active today. T2 and T3 run in parallel as research and enterprise tracks.

## Consequences

- **Positive:** Pronunciation correctness improves with every recording batch
- **Positive:** Region-scoped cache ensures Suryapet audio never leaks to other regions
- **Negative:** T2 (VibeVoice) requires reconstructing inference code from HF weights
- **Negative:** T3 (Sarvam clone) is enterprise-only with undefined pricing/timeline

## Alternatives Considered

- **Replace Sarvam with self-hosted VITS/YourTTS** — Rejected: no production-grade Telugu support, GPU infra cost unjustified at current volume
- **Manual phoneme-level SSML** — Rejected: Sarvam Bulbul v3 does not support SSML
- **Wait for Sarvam to add regional Telugu speakers** — Rejected: no public roadmap, timeline unknown

## References

- [^14]: VECL-TTS. (2024). Voice Identity and Emotional Style Controllable Cross-Lingual Text-to-Speech. *arXiv:2406.08076*.
- [^11]: Sarvam AI. (2025). Bulbul V3: Next-Generation TTS for Indian Languages. *Blog*. https://www.sarvam.ai/blogs/bulbul-v3
- [^9]: Microsoft Research. (2025). VibeVoice Repository. *GitHub*. https://github.com/microsoft/VibeVoice
