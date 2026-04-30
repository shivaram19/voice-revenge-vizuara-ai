# BFS-006: Indian-Name STT Landscape — Mapping the Field

> **Date:** 2026-04-30
> **Scope:** Breadth-first landscape mapping of speech-to-text vendors that *might* outperform Deepgram Nova-3 on Indian names + Telugu code-switching for the Jaya High School deployment. Identifies candidates worth a follow-up DFS, eliminates the rest.
> **Research Phase:** BFS — landscape mapping only. No DFS-grade reproduction here.
> **Status:** Active. Drives a follow-up DFS-NN (TBA) on the lead candidate.

---

## 1. Why this BFS exists

The 2026-04-30 production calls produced concrete evidence of STT errors on Indian names:

- *"Aarav"* heard as *"Aera"* / *"Aras"* / *"Arau"* across three calls (Deepgram Nova-3 `language=multi`).
- *"Suryapet"* heard as *"Surya Pent"*.
- *"Shiv Ram"* heard as *"Shivram"* / *"Janvi"* (mis-diarisation + transliteration).

These are not edge cases — they are the *modal* parent and child names in our deployment. A 30%+ error rate on the most-used proper nouns is a product-quality issue. Per AGENTS.md §Decision Authority "Cite before you commit," this BFS surveys what else is on the market before any swap is proposed.

---

## 2. Candidates in scope

Five candidate vendors / model families. The shortlist was assembled from an initial web sweep, the criterion being: **claims to handle Indian languages or Indian-accent English natively, with streaming, in 2025-2026**.

| # | Vendor | Model | License |
|---|---|---|---|
| 1 | Deepgram (incumbent) | Nova-3 Multilingual | Closed, vendor-API |
| 2 | Sarvam AI | Saaras V3 | Closed, vendor-API (Indian) |
| 3 | AI4Bharat (IIT Madras) | IndicConformer 600M / Indic-Whisper | Open-source (Apache-style) |
| 4 | Reverie | Custom Indian-language ASR | Closed, vendor-API (Indian) |
| 5 | Bhashini (Govt of India consortium) | Multiple — IITB/IITM/IIITH/CDAC | Open / govt-funded |
| 6 | Google Cloud | Speech-to-Text | Closed, vendor-API |

Out of scope (knowingly): Whisper-base / faster-whisper / Distil-Whisper — already covered in DFS-01; underperforms on Indian-accent English per [^Radford2022]. AssemblyAI, AWS Transcribe, Azure Speech — limited Telugu support per [^AssemblyAI2026][^Smallest2026].

---

## 3. Per-candidate landscape facts (collected this session)

### 3.1 Deepgram Nova-3 (incumbent)

- **Languages with code-switching support:** English, Spanish, French, German, **Hindi**, Russian, Portuguese, Japanese, Italian, Dutch [^Deepgram2025MultiLang]. **Telugu is not in this list.**
- **Telugu support:** not listed in current models documentation. South Asia expansion "planned" but not delivered as of 2026-04 [^Deepgram2025NovaIntro].
- **WER claim:** "54.2% reduction in streaming WER vs competitors" (vendor benchmark, English-centric) [^Deepgram2025NovaIntro]. Indic-specific benchmarks not published by vendor.
- **Streaming:** native, well-tested in our deployment.
- **Pricing:** $0.0077 / min streaming [^Deepgram2025Pricing].

**Verdict for our use case:** Strong on English and Hindi-English code-switch; **structurally insufficient for Telugu code-switching.** The observed name errors are a symptom of this gap, not a tunable parameter.

### 3.2 Sarvam AI Saaras V3

- **Languages:** 22 official Indian languages + English, including **Telugu (te-IN)** as a first-class target [^SarvamV3].
- **WER:** ~19.3% on the **IndicVoices benchmark** subset of 10 most-popular languages; v2.5 was ~22% (June 2025) [^SarvamV3]. Independent claim.
- **Streaming:** native, low-latency [^SarvamV3].
- **Code-mixing:** explicit design goal; vendor announcement specifically calls out "code-mixed speech and noise" [^News9Sarvam2026].
- **Pricing:** Indian SaaS pricing tier (specifics need a DFS).
- **3rd-party integrations:** Pipecat, Bolna [^PipecatSarvam].

**Verdict:** Top candidate for DFS validation. Purpose-built for our exact problem class. Indian vendor — alignment with parent demographic + DPDP Act jurisdictional cleanliness.

### 3.3 AI4Bharat IndicConformer 600M / Indic-Whisper

- **Languages:** all 22 official Indian languages including Telugu [^AI4BharatASR].
- **WER:** lowest WER on 39 of 59 benchmarks in Vistaar — AI4Bharat's open evaluation suite spanning 12 Indian languages with 10,700+ labelled hours [^AI4BharatVistaar].
- **License:** open-source on HuggingFace (`ai4bharat/indic-conformer-600m-multilingual`) — self-hosting required.
- **Streaming:** Conformer architecture supports it; production wiring is on us.
- **Cost:** infra-only (no per-minute API fee), but self-host operational burden.
- **Code-switching:** explicit research focus.

**Verdict:** Strong open-source backup. If Sarvam DFS shows quality wins but unacceptable per-call cost or vendor lock-in, IndicConformer is the fall-back.

### 3.4 Reverie

- **Languages:** Bengali, Marathi, Tamil, **Telugu**, Kannada, Malayalam, Gujarati, Punjabi, Assamese, Odia, more — purpose-trained per language [^Reverie2026].
- **Streaming:** real-time available [^Reverie2026].
- **WER:** vendor self-comparison vs Deepgram exists but treated as Tier-3 (vendor blog, not peer-reviewed). Independent benchmarks not located in this BFS.
- **Code-switching:** claimed.

**Verdict:** Plausible candidate but evidence is currently vendor-blog-only. Promote to DFS only if Sarvam fails.

### 3.5 Bhashini (Government of India consortium)

- **Languages:** Telugu + 21 more, served by IITB / IITM / IIITH / CDAC research groups [^Bhashini].
- **Streaming:** WebSocket ASR API (`ULCASocketClient`) [^BhashiniWS].
- **License:** open / govt-funded, free.
- **Hidden cost:** model-quality varies by partner; SLAs are research-grade not production-grade.
- **Code-switching:** documented but partner-specific.

**Verdict:** Strategic backup (national-asset, free, sovereign). Currently lower priority than commercial Sarvam given operational predictability concerns. Tracking only.

### 3.6 Google Cloud Speech-to-Text

- **Languages:** 125+ including Telugu [^GoogleSTT].
- **Indian-accent performance:** "inconsistent accuracy for Indian accents, dialects, and mixed-language speech" — multiple Tier-3 sources concur [^Smallest2026][^Reverie2026].
- **Code-switching:** general capability exists; Telugu-English specifically not benchmarked in vendor docs.
- **Pricing:** $0.024 / min — ~3× Deepgram, ~similar to Sarvam.

**Verdict:** Eliminated. We would not deliberately choose a global model that the vendor's own documentation says struggles with Indian accents when an Indian-specific alternative exists at comparable cost.

---

## 4. Comparison matrix

| Dimension | Nova-3 | Saaras V3 | IndicConformer | Reverie | Bhashini | Google STT |
|---|---|---|---|---|---|---|
| Telugu | ❌ | ✅ first-class | ✅ first-class | ✅ first-class | ✅ partner-dependent | ✅ generic |
| Telugu↔English code-switch (live) | ❌ | ✅ designed | ✅ research focus | ✅ claimed | ✅ varies | ⚠ inconsistent |
| Streaming | ✅ | ✅ | ✅ (self-host) | ✅ | ✅ | ✅ |
| Indian-name WER (qualitative) | poor (observed) | strong | strong | claimed | varies | weak |
| Independent benchmark | English only | IndicVoices ~19.3% | Vistaar 39/59 wins | none located | none located | English-strong |
| Pricing | $0.0077/min | TBD (DFS) | infra only | TBD | free | $0.024/min |
| Vendor jurisdiction | US | India | India (academic) | India | India (govt) | US |
| Compliance posture (DPDP Act) | data egress | sovereign | sovereign | sovereign | sovereign | data egress |

---

## 5. BFS recommendation → DFS gate

**Promote to DFS:**

1. **Sarvam Saaras V3** — strongest Tier-1 evidence (IndicVoices 19.3% WER), explicit code-mix design, sovereign jurisdiction. DFS would measure: actual WER on our recording corpus (Aarav / Sneha / Lakshmi / Shiv Ram / Suryapet), telephony 8 kHz μ-law performance, end-to-end streaming latency vs Nova-3, and per-call cost.

2. **AI4Bharat IndicConformer** — as the open-source backup, if Saaras V3 has unacceptable cost or vendor risk. DFS would measure the same things plus the operational cost of self-hosting on Container Apps.

**Do NOT promote yet:**
- Reverie, Bhashini, Google — eliminated by §3.

---

## 6. Open questions for the DFS

1. Independent WER on our specific recording corpus (the 7 calls placed in this session, with ground-truth transcripts).
2. Code-switching behaviour across a single utterance: *"My child's name is Aarav, paid kattam already"* — does the model preserve both languages?
3. **Numerics + named entities**: ₹15,000 / "fifteen thousand rupees" — Sarvam's claim of best-CER on numerics needs validation [^SarvamBulbul] (note: that claim is for Bulbul TTS, not Saaras STT — must be verified for STT separately).
4. Latency comparison: Saaras streaming first-partial vs Nova-3 ~80ms time-to-first-partial baseline.
5. Behaviour under telephony codec (G.711 μ-law 8 kHz) vs studio audio — Sarvam's Bulbul has a separate 8 kHz benchmark [^SarvamBulbul]; Saaras may not.

---

## References

> Source-tier policy per AGENTS.md: Tier 1 peer-reviewed / canonical, Tier 2 vendor docs / public-data sources, Tier 3 vendor blog posts (current SaaS defaults — NOT normative).

### Tier 1 — Peer-reviewed / academic

[^AI4BharatVistaar]: AI4Bharat. *Vistaar: Diverse Benchmarks and Training Sets for Indian Language ASR.* github.com/AI4Bharat/vistaar (paper + dataset).
[^Radford2022]: Radford, A., et al. (2022). *Robust Speech Recognition via Large-Scale Weak Supervision.* arXiv:2212.04356.

### Tier 2 — Vendor / official documentation

[^SarvamV3]: Sarvam AI. *Saaras V3 model card.* sarvam.ai/blogs/asr.
[^AI4BharatASR]: AI4Bharat IIT Madras. *Automatic Speech Recognition area page.* ai4bharat.iitm.ac.in/areas/asr.
[^Deepgram2025NovaIntro]: Deepgram. *Introducing Nova-3.* deepgram.com/learn/introducing-nova-3-speech-to-text-api.
[^Deepgram2025MultiLang]: Deepgram. *Nova-3 Expands with 11 New Languages.* deepgram.com/learn/deepgram-expands-nova-3-with-11-new-languages-across-europe-and-asia.
[^Deepgram2025Pricing]: Deepgram pricing page. deepgram.com/pricing.
[^GoogleSTT]: Google Cloud Speech-to-Text language list. cloud.google.com/speech-to-text.
[^Bhashini]: Bhashini consortium API documentation. bhashini.gitbook.io/bhashini-apis.
[^BhashiniWS]: Bhashini WebSocket ASR API. dibd-bhashini.gitbook.io/bhashini-apis/websocket-asr-api.

### Tier 3 — Vendor blog / industry coverage (NOT normative)

[^News9Sarvam2026]: News9live. *Sarvam Saaras V3 targets code-mixed speech.* (Industry coverage of vendor claims.)
[^PipecatSarvam]: Pipecat docs — Sarvam integration. docs.pipecat.ai/server/services/stt/sarvam.
[^Reverie2026]: Reverie. *Deepgram vs Reverie multilingual accuracy 2026* — vendor self-comparison; cited only as evidence Reverie supports Telugu, not as evidence of relative quality.
[^AssemblyAI2026]: AssemblyAI. *Google Cloud STT alternatives 2026* — third-party landscape; not normative.
[^Smallest2026]: Smallest.ai. *Is Google Cloud STT Still the Right Choice 2026* — third-party landscape; not normative.
[^SarvamBulbul]: Sarvam AI. *Bulbul V3 model card.* sarvam.ai/blogs/bulbul-v3 (Tier-2; cited specifically for telephony 8 kHz benchmark methodology).
