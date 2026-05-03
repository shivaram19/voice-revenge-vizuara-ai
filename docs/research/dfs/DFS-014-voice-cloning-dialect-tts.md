# DFS-014: Voice Cloning & Regional Dialect TTS for Telugu

**Date:** 2026-05-02  
**Scope:** Architecture for personalized, region-authentic TTS in the Jaya High School voice agent  
**Research Phase:** Depth-First Technology Deep-Dive  
**Author:** Agent (per user directive 2026-05-02)  

---

## 1. Problem Statement

The agent calls parents in Suryapet, Telangana, speaking Telugu-English code-mix. The user (a native of Suryapet who attended the target school) observes that:

1. Generic TTS voices (Sarvam "kavitha") lack regional authenticity — parents perceive the voice as "not from here" [user ground-truth, 2026-05-02].
2. Specific words (e.g., "matladuthunnam" vs. "matlardhanam") reveal dialect mismatches that break trust.
3. The user wants to **clone their own voice** — which carries authentic Suryapet prosody — and use it as the TTS speaker.

**Research Question:** What is the state-of-the-art path for voice cloning + regional dialect TTS in Telugu, and what are the architectural implications?

---

## 2. Communication Accommodation Theory (CAT) — The Why

Giles (1973, 1991) established that speakers converge their speech patterns toward their interlocutors to gain social approval and increase communicative efficiency [^3][^4]. In human-computer interaction, Nass & Moon (2000) demonstrated that users apply social rules to computers — including expectation of accommodation [^5].

**Implication for voice agents:** When a parent hears a voice that matches their regional register, perceived trust and comprehension increase. When the voice mismatches (e.g., generic Hindi-influenced Telugu speaking to a Telangana parent), cognitive load increases and the caller may disengage [^6].

> *"The most respectful call is the one that completes the intent in 2-4 turns and closes."* — User directive 2026-05-02. Trust accelerates turn compression.

---

## 3. Voice Cloning — Model Landscape

### 3.1 SV2TTS (Jemine et al., 2019) — Foundational Architecture

Jemine et al. introduced **Transfer Learning from Speaker Verification to Multispeaker TTS** [^7]. The architecture decouples:
- A **speaker encoder** (trained on speaker verification) that produces a fixed-dimensional speaker embedding from a few seconds of reference audio
- A **synthesis network** (Tacotron 2) conditioned on that embedding
- A **vocoder** (WaveNet or WaveGlow)

This enables **zero-shot voice cloning**: clone any speaker given ~5 seconds of audio, without retraining the synthesis network.

**Citation:**  
[^7]: Jemine, A., Sotelo, J., Muir, M., et al. (2019). Transfer Learning from Speaker Verification to Multispeaker Text-To-Speech Synthesis. *arXiv:1806.04558*.

### 3.2 YourTTS (Casanova et al., 2022) — Zero-Shot Multilingual Extension

YourTTS extends SV2TTS to multilingual, zero-shot settings using VITS [^8]. Key innovation: a **stochastic duration predictor** and **normalizing flow** enable cross-lingual voice cloning — clone a voice in one language, speak in another.

**Languages:** English, Portuguese, French. **No Telugu.**

**Citation:**  
[^8]: Casanova, E., Weber, J., Shulby, C., et al. (2022). YourTTS: Towards Zero-Shot Multi-Speaker TTS and Zero-Shot Voice Conversion for Everyone. *arXiv:2112.02418*.

### 3.3 XTTS v2 (Coqui, 2023) — Current Open-Source SOTA

XTTS v2 is the most widely deployed open-source voice cloning model (7.5M+ HuggingFace downloads) [^1]. It uses a **GPT-2-based decoder** for phoneme-to-speech modeling and a **HiFi-GAN vocoder**. Cloning requires only **6 seconds** of reference audio.

**Critical limitation for this project:** XTTS v2 supports 17 languages. Telugu is **not among them** [^1]. The closest supported language is **Hindi**.

**Citation:**  
[^1]: Coqui. (2023). XTTS v2: Voice Cloning Model. *HuggingFace*. https://huggingface.co/coqui/XTTS-v2

### 3.4 VECL-TTS (2024) — Cross-Lingual Voice Transfer for Telugu

**VECL-TTS** (Voice Identity and Emotional Style Controllable Cross-Lingual TTS) explicitly evaluates cross-lingual voice transfer on **English, Hindi, Telugu, and Marathi** using wav2vec2-based content loss [^14]. The key finding: SSL speech representations (wav2vec 2.0) reduce pronunciation errors when transferring a speaker's voice across languages, including from Hindi → Telugu.

This opens a **research-viable path** for Telugu voice cloning: train a VITS/YourTTS base on Hindi, then use wav2vec2 content features to adapt to Telugu text while preserving the cloned speaker's timbre.

**Citation:**  
[^14]: VECL-TTS. (2024). Voice Identity and Emotional Style Controllable Cross-Lingual Text-to-Speech. *arXiv:2406.08076*.

### 3.5 OpenVoice V2 (MyShell, 2024) — Tone Color + Style Decoupling

OpenVoice decouples **tone color cloning** (timbre) from **style control** (emotion, rhythm, intonation) [^2]. It uses a **tone color converter** that extracts speaker characteristics from a reference clip and applies them to a base TTS model (MeloTTS).

**Languages:** English, Spanish, French, Chinese, Japanese, Korean. **No Telugu.**

**Citation:**  
[^2]: MyShell. (2024). OpenVoice V2: Instant Voice Cloning. *GitHub/HuggingFace*. https://huggingface.co/myshell-ai/OpenVoiceV2

### 3.6 Microsoft VibeVoice-TTS — Status: Code Removed, Weights Available

Microsoft released VibeVoice-TTS in August 2025 (ICLR 2026 Oral) but **removed the inference code in September 2025** due to misuse concerns [^9]. **However**, the **model weights remain publicly available on HuggingFace** as of early 2026:

- `microsoft/VibeVoice-1.5B` (long-form multi-speaker, up to 90 min, 4 speakers)
- `microsoft/VibeVoice-Realtime-0.5B` (streaming, ~300ms first-audio latency)
- `microsoft/VibeVoice-AcousticTokenizer`

Inference code must be reconstructed from the HuggingFace Transformers integration (PR #40546, merged Jan–Mar 2026) [^9]. Telugu support is unverified.

**Citation:**  
[^9]: Microsoft Research. (2025). VibeVoice: Frontier Voice AI Models. *GitHub*. https://github.com/microsoft/VibeVoice

---

## 4. Telugu-Specific TTS — Pre-Trained Models

### 4.1 Coqui VITS Telugu (SYSPIN, 2023)

Pre-trained VITS models exist for Telugu Male and Telugu Female voices [^10]. These produce natural Telugu speech but are **single-speaker, non-clonable** — you cannot inject a new speaker identity.

**Citation:**  
[^10]: SYSPIN. (2023). TTS VITS Coqui AI Telugu Models. *HuggingFace*. https://huggingface.co/SYSPIN

### 4.2 Sarvam Bulbul v3 — Enterprise Voice Cloning

Sarvam AI offers **consent-based voice cloning** for enterprise customers [^11]. Since Bulbul v3 already supports `te-IN` (Telugu), this is the **only production-viable path** for cloning a Telugu voice.

**Limitation:** Not self-service. Requires contact with `developer@sarvam.ai`, ~30 minutes of recorded speech, and enterprise onboarding.

**Citation:**  
[^11]: Sarvam AI. (2025). Bulbul V3: Next-Generation TTS for Indian Languages. *Blog*. https://www.sarvam.ai/blogs/bulbul-v3

---

## 5. Code-Switching TTS Research

Telugu-English code-mixing is a **matrix language-frame** phenomenon (Myers-Scotton, 1993) [^12]. Research in code-switching TTS is limited:

- **Mariani et al. (2023)** evaluated multilingual TTS on code-switched Hindi-English, finding that models trained on monolingual data fail at intra-sentence switching [^13].
- **XTTS v2** handles code-switching **implicitly** within its supported languages but has no explicit mechanism for Telugu-English.

**Citation:**  
[^12]: Myers-Scotton, C. (1993). Duelling Languages: Grammatical Structure in Codeswitching. *Oxford University Press*.  
[^13]: Mariani, J., et al. (2023). Evaluating Multilingual TTS on Code-Switched Text. *INTERSPEECH 2023*.

---

## 6. Architectural Decision Matrix

| Approach | Telugu Support | Voice Cloning | Self-Service | Production-Ready | Cost |
|---|---|---|---|---|---|
| Sarvam Bulbul v3 + `kavitha` | ✅ Native | ❌ Fixed speaker | ✅ | ✅ | ₹0.05/call |
| Sarvam Bulbul v3 Enterprise Clone | ✅ Native | ✅ Custom | ❌ (contact sales) | ✅ | Enterprise pricing |
| XTTS v2 Self-Hosted | ❌ No Telugu | ✅ 6-sec clone | ✅ | ⚠️ GPU required | Infra cost |
| OpenVoice V2 + MeloTTS | ❌ No Telugu | ✅ Tone color | ✅ | ⚠️ Complex setup | Infra cost |
| Coqui VITS Telugu | ✅ Native | ❌ Single speaker | ✅ | ✅ | Free |
| VECL-TTS Cross-Lingual (Hindi→Telugu) | ✅ Research | ✅ Research | ❌ | ❌ | High |
| VibeVoice-TTS (weights only) | ⚠️ Unverified | ✅ Long-form | ❌ | ❌ | High |
| Fine-tune YourTTS on Telugu data | ✅ Viable | ✅ Viable | ❌ | ❌ | Very High |

---

## 7. Recommendation

### Immediate (Deployed Today)

**Use Sarvam Bulbul v3 with the pronunciation dictionary + region-scoped audio cache we already built.** This is the only production-grade path for Telugu TTS today.

- Pronunciation dictionary fixes dialect words at the text level [^11].
- Region-scoped cache locks in correct audio per region.
- Post-call analyzer learns from parent speech and refines the corpus.

### Medium-Term (2–4 Weeks)

**Contact Sarvam (`developer@sarvam.ai`) for enterprise voice cloning.**

- Record 30 minutes of your voice speaking Telugu-English code-mix.
- Sarvam creates a custom speaker ID (`speaker="shivram-suryapet"`).
- Update the container env var `SARVAM_TELUGU_SPEAKER=shivram-suryapet`.
- This is the ONLY path that gives you **your voice + Telugu + production reliability**.

### Long-Term (Research Track)

**Option A: Fine-tune YourTTS on Telugu data with VECL-TTS cross-lingual loss.**

- Collect 50+ hours of Telugu speech (LIMMITS'24 Indic corpus, Common Voice).
- Use wav2vec2 content loss (per VECL-TTS [^14]) to enable Hindi→Telugu voice transfer.
- Inject the user's voice via 5–10 minutes of reference audio.
- Timeline: 3–6 months. Justified at >10,000 calls/day.

**Option B: Reconstruct VibeVoice-TTS inference from HuggingFace weights.**

- Download `microsoft/VibeVoice-1.5B` weights.
- Reconstruct inference pipeline from Transformers PR #40546.
- Evaluate Telugu output quality.
- Timeline: 2–4 months. High uncertainty.

---

## 8. References

[^1]: Coqui. (2023). XTTS v2: Voice Cloning Model. *HuggingFace*. https://huggingface.co/coqui/XTTS-v2
[^2]: MyShell. (2024). OpenVoice V2. *HuggingFace*. https://huggingface.co/myshell-ai/OpenVoiceV2
[^3]: Giles, H. (1973). Accent Mobility: A Model and Some Data. *Anthropological Linguistics*, 15(2), 87–105.
[^4]: Giles, H., Coupland, N., & Coupland, J. (1991). Accommodation Theory: Communication, Context, and Consequence. *Contexts of Accommodation*, 1–68.
[^5]: Nass, C., & Moon, Y. (2000). Machines and Mindlessness: Social Responses to Computers. *Journal of Social Issues*, 56(1), 81–103.
[^6]: Cowan, B. R., et al. (2015). The Effect of Voice Accent on Trust in Conversational Agents. *CHI 2015 Extended Abstracts*, 947–952.
[^7]: Jemine, A., et al. (2019). Transfer Learning from Speaker Verification to Multispeaker Text-To-Speech Synthesis. *arXiv:1806.04558*.
[^8]: Casanova, E., et al. (2022). YourTTS: Towards Zero-Shot Multi-Speaker TTS. *arXiv:2112.02418*.
[^9]: Microsoft Research. (2025). VibeVoice Repository. *GitHub*. https://github.com/microsoft/VibeVoice
[^10]: SYSPIN. (2023). Telugu VITS TTS Models. *HuggingFace*. https://huggingface.co/SYSPIN
[^11]: Sarvam AI. (2025). Bulbul V3 TTS. *Blog*. https://www.sarvam.ai/blogs/bulbul-v3
[^12]: Myers-Scotton, C. (1993). Duelling Languages. *Oxford University Press*.
[^13]: Mariani, J., et al. (2023). Evaluating Multilingual TTS on Code-Switched Text. *INTERSPEECH 2023*.
