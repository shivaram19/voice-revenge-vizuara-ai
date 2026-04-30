# DFS-010: Telugu Code-Switching + Prosody for Outbound Voice Agent

> **Date:** 2026-04-30
> **Scope:** When and how to render Telugu in our TTS output without sounding stilted, in service of the Jaya High School fee-call use case where every parent has `language_preference` as either *English* or *Telugu*. Names + greetings + closings need to sound right *to a Telugu speaker*, even when the body of the call is in English.
> **Research Phase:** DFS — vertical depth into Telugu prosody and code-switch architecture.
> **Status:** Active. Drives a new ADR (TBA) on dual-TTS architecture, plus immediate copy-tier polish landable today.

---

## 1. Why this DFS

The 2026-04-30 production calls demonstrated that parents respond positively to Telugu cues — *"Dhanyavaadalu, sir. Goodbye!"* (recorded on call 4) emerged organically from the LLM and was the warmest moment of the conversation. But the rest of the agent's speech is rendered through Deepgram Aura (American/British/Australian English voices), which is structurally **incapable of speaking Telugu** [^DeepgramAuraDocs]. We have a mismatch: a Telugu-native demographic + an English-only TTS + occasional Telugu phrases shoehorned into Aura's pronunciation.

This DFS asks two questions:

1. **What prosodic primitives matter for Telugu-English code-switch on the phone?** (The linguistics question.)
2. **How do we render them in production at <1 s end-to-end latency?** (The engineering question.)

DFS-010 takes a strong position by the end: we need a **dual-TTS architecture** for Telugu-preference parents, but we can do meaningful copy-tier polish today with the single-TTS we already have.

---

## 2. Linguistic primitives — what's actually different about Telugu

### 2.1 Telugu is syllable-timed, English is stress-timed

Indian languages including Telugu are **syllable-timed**: each syllable carries roughly equal duration weight, and pitch + duration mark prosodic structure rather than stress alternation [^SIToBI2025]. English is stress-timed: alternating stressed/unstressed syllables compress unstressed ones.

When an English-trained TTS speaks an Indian word like *"Aarav"* (अराव — three Telugu syllables, all syllable-equal), it applies English stress patterns and clips the unstressed syllables, producing the *"Aera"* / *"Arau"* mishearings we saw in the call recordings — the *output* sounds wrong even before STT mis-transcribes it. This is not a tuning problem; it is the wrong rhythm primitive.

### 2.2 Honorifics carry conversational respect; absence is rude

Telugu has a rich honorific system [^TalkpalHonorifics][^AddressTermsTelugu2016]:

- **Garu** (గారు) — universal respect suffix, gender-neutral, attached after name or designation. *"Lakshmi Garu"*, *"Sir Garu"*. Used liberally in any non-intimate adult conversation.
- **Sri / Srimati** (శ్రీ / శ్రీమతి) — formal "Mr./Mrs." prefix. Used in writing or very formal speech.
- **Vaaru** (వారు) — plural honorific pronoun for a single respected person. Highly formal.
- **Family-kinship terms used for non-relatives** — *Amma* / *Avva* for elder women, *Ayya* / *Taata* for elder men. Markers of warmth, not just respect.

The current English greeting *"Namaste sir"* uses a single honorific (*sir*). A Telugu-preference parent would expect at least **Garu** to be available — its absence reads as cold even when the rest of the speech is warm.

### 2.3 Code-switching is the default register, not the exception

Sociolinguistic research consistently finds that code-mixing/code-switching between Indian languages and English is "very natural in everyday speech in the Indian subcontinent" [^EverydaySpeech2024]. Parents do not switch to "pure Telugu" or "pure English" registers when speaking to school staff — they shift mid-utterance. *"Naa pillavadu paid kattadu already"* ("My child has paid already" — Telugu + English mid-clause) is the modal sentence shape.

This means the question is not *should we add Telugu* but *how we share the conversational floor with English in the same turn*.

### 2.4 Pitch and duration carry illocutionary force

Telugu uses pitch contour + syllable duration — not stress alternation — to mark questions, deference, and warmth [^IEEE2014TeluguAccent]. A flat-pitch Aura rendering of *"Garu"* sounds robotic; the same word with a slight rising contour and longer final syllable reads as warm acknowledgment.

This is exactly the kind of nuance Aura is designed not to deliver: Deepgram's stated direction is "moving away from SSML" toward "naturally expressive" English voices [^DeepgramSSMLStance]. The expressive primitives are baked into English speech patterns, not Telugu.

---

## 3. The state of TTS for our requirement

### 3.1 Deepgram Aura (incumbent)

- Voices: American, British, Australian, Irish, Filipino English; Spanish (Mexican / Peninsular / etc.) [^DeepgramAuraDocs].
- **No Telugu, no Hindi, no Indian language support.** Aura-2 expansion to Dutch / French / German / Italian / Japanese announced; no Indic on the roadmap [^DeepgramAura2Expansion].
- **No SSML support**, and Deepgram has explicitly said SSML is not on the roadmap [^DeepgramSSMLStance]. We cannot tune rate/pitch per-phrase; we get whatever the model outputs.
- 8 kHz telephony output: yes, supported, our current production path.

**Verdict for Telugu:** Structurally cannot do it. Telugu phrases rendered via Aura are English-phonetic transliteration; they sound like an American voice trying to read Sanskrit. *Acceptable for occasional single words* (Namaste, Dhanyavaadalu, Garu) but not for full Telugu sentences.

### 3.2 Sarvam Bulbul V3

- 35+ voices across 11 Indian languages including **Telugu (te-IN)** [^SarvamBulbul].
- Built specifically for Indian-language TTS quality with **explicit telephony (8 kHz) benchmark** — Sarvam's claim is "Bulbul V3 is the clear top performer across all competitors" at 8 kHz, where ElevenLabs leads only at studio quality [^SarvamBulbul].
- Independent third-party blind A/B vs ElevenLabs / Cartesia [^SarvamBulbul] — vendor-supplied but methodologically described.
- Supports code-switching natively and was evaluated on "code-mixing, Romanized text, abbreviations" [^SarvamBulbul].
- Pipecat + Bolna integrations exist [^PipecatSarvamTTS][^BolnaSarvam].

**Verdict:** Production-ready Telugu TTS that explicitly handles our exact telephony codec.

### 3.3 AI4Bharat Indic Parler-TTS / IndicF5

- Open-source, 21 languages including Telugu [^AI4BharatParlerTTS].
- IndicF5 is the latest model from AI4Bharat [^AI4BharatIndicF5].
- IndicVoices-R: 1,704 hours, 10,496 speakers, 22 languages — the dataset behind these models — is published, peer-reviewed, NeurIPS 2024 [^IndicVoicesR2024].
- Self-host required (HuggingFace weights).
- MOS-evaluated; vendor claims "exceptional performance" for native speakers; specific MOS numbers not surfaced in this BFS but documented in the dataset paper.

**Verdict:** Open-source backup if commercial Bulbul has cost or jurisdictional issues.

### 3.4 What today (Aura-only) can deliver

A small set of *Telugu loanwords* that English-speaking voices can phonetically approximate without sounding ridiculous:

- *Namaste* — universally rendered acceptably by American English TTS.
- *Dhanyavaadalu* — already observed working in production (call 4).
- *Garu* — phonetically *"GAH-roo"*; American English voice can speak it.
- *Sir / Madam* — already in active use.

Anything more (full sentences, *"మీ పిల్లవాడు"*) would not work in Aura.

---

## 4. Architectural options

### Option A: Stay with Aura-only; English+loanwords only
**Description:** Keep current pipeline. Polish copy to use a small Telugu-loanword vocabulary in greetings, honorifics, and closings.

- Cost: zero infra change.
- Quality: marginal improvement over today; bounded by what English TTS can pronounce.
- Risk: low.
- Latency impact: zero.
- Effort: ~2 hours of prompt + scenario edits.

### Option B: Add Sarvam Bulbul as a second TTS adapter
**Description:** Implement `SarvamTTSAdapter` behind the existing `TTSPort`. Receptionist routes to Bulbul when `record.language_preference == "Telugu"`, otherwise to Aura.

- Cost: per-call TTS roughly doubles when Bulbul is selected. (Need DFS-NN to quantify; vendor pricing tier likely competitive with Aura.)
- Quality: substantial improvement for Telugu-preference parents.
- Risk: medium — new vendor dependency, jurisdictional move (Sarvam = India = good for DPDP, see Bidirectional X-2).
- Latency impact: TBD; Sarvam claims real-time. Need DFS-grade measurement.
- Effort: ~1.5 days (adapter + tests + lifespan wiring + metric instrumentation).

### Option C: Sentence-level dual-TTS routing
**Description:** Split a single agent turn into Telugu and English fragments; Bulbul speaks the Telugu fragments, Aura speaks the English fragments; concatenate the audio chunks at sub-sentence boundaries.

- Cost: highest — two TTS calls per turn for code-switched turns.
- Quality: the linguistically correct answer; matches how Telugu-English speakers actually code-switch.
- Risk: high — concatenated audio with two different speaker identities will sound like two different agents (the "two-women-and-a-man" failure mode the project already fixed in `tts_prosody.py`'s uniform-voice policy).
- Latency impact: significant — two sequential synthesis calls.
- Effort: ~3 days, plus a large UX risk.

### Option D: Wait for Aura Indic
**Description:** Do nothing; let Deepgram add Indic when they expand.

- Risk: indefinite timeline; Aura-2 announcement covered EU + East Asia, not Indic [^DeepgramAura2Expansion].
- This is the "ostrich" option. Reject.

---

## 5. Recommendation

**Land Option A this week. Validate Option B in DFS-NN. Do not pursue Option C.**

Reasons:

- **Option A** is reversible, low-risk, and immediately improves the Telugu-preference parent experience. Specifically: agent's greeting, honorifics, and closings get a curated Telugu-loanword lexicon that Aura can pronounce.
- **Option B** is the right long-term answer; deserves a DFS to measure pricing, latency, and audio-quality on our actual telephony path before committing.
- **Option C** is what the *literature* says is right but our existing project memory tells us multi-voice causes more confusion than gain (the "two women and a man voice" feedback that produced the uniform-voice policy in commit `3254a5a`). Defer until Bulbul has demonstrated steady single-voice quality first.

---

## 6. Concrete copy changes (Option A — landable today)

The `_greeting_for(record)` in `EducationReceptionist` returns one greeting today. Polish it for Telugu-preference parents by using **Garu** and matching the kinship register described in §2.2:

```
# Today (English-preference)
"Namaste sir. Calling from Jaya High School. Is this a good time to talk, sir?"

# Proposed (Telugu-preference)  — Aura can speak this
"Namaste {salutation_garu}. Calling from Jaya High School.
 Mee child gaariki related a small message undi. Is this a good time, sir?"

# Where {salutation_garu} = "Garu" if married parent; "Sir Garu" / "Madam Garu" 
# in formal mode.
```

The middle Telugu-English mid-clause sentence is exactly the modal register parents expect (§2.3). Aura will render *"Mee child gaariki"* phonetically — not perfectly, but adequately — and the parent's familiarity with the register fills in the rest.

Honorific suffix application (across all scenarios):
- For PARTIAL/UNPAID flows where the agent says the parent's name: append *Garu*. *"Lakshmi Devi Garu, …"*.
- Closings: *"Dhanyavaadalu, Garu. Have a peaceful day."*.

The change set is ~15 lines across `_greeting_for`, the scenario openings/closings, and a small string-template helper for *Garu* formatting. No new infrastructure.

---

## 7. Open questions / future work

1. **DFS-NN: Sarvam Bulbul V3 reproduction on our telephony path.** Measure end-to-end latency from text → 8 kHz μ-law audio → Twilio playback; measure perceptual quality against Aura on a controlled corpus of our actual scenario openings; measure cost.
2. **Bidirectional X-3: Code-switch boundary detection in the LLM's output.** If Option B lands, the receptionist needs to *segment* an LLM turn into Telugu / English chunks for routing. Does the LLM already mark code-switch boundaries, or do we need a classifier?
3. **DPDP Act jurisdiction**: Sarvam is India-resident; switching makes the data plane sovereign. This couples to ADR-017 (Bidirectional X-2 in the goals charter).
4. **Telugu STT**: complementary to this DFS — see BFS-006 for the STT side. The two questions are independent (STT and TTS) but the holistic answer is "use an Indian-resident vendor for both".
5. **Voice-identity continuity**: if we ever go to Option C, we need to A/B test whether parents notice the speaker change at code-switch boundaries. There may be cognitive-warmth research that tells us whether the linguistic correctness of dual-TTS outweighs the speaker-discontinuity penalty.

---

## References

> Tiers per AGENTS.md: Tier 1 = peer-reviewed / canonical; Tier 2 = vendor docs / public data; Tier 3 = industry coverage (NOT normative).

### Tier 1 — Peer-reviewed / canonical

[^SIToBI2025]: Mahanta, A., et al. (2025). *SIToBI: A Speech Prosody Annotation Tool for Indian Languages.* arXiv:2502.09661. Foundation for the syllable-timed-vs-stress-timed claim.
[^IndicVoicesR2024]: Sankar, A., et al. (2024). *IndicVoices-R: A Massive Multilingual Multi-speaker Speech Corpus for Scaling Indian TTS.* NeurIPS 2024 Datasets & Benchmarks Track. proceedings.neurips.cc/paper_files/paper/2024/file/7dfcaf4512bbf2a807a783b90afb6c09-Paper-Datasets_and_Benchmarks_Track.pdf
[^IEEE2014TeluguAccent]: Bharath, K. P., et al. (2014). *Accent detection of Telugu speech using prosodic and formant features.* IEEE Conf. Communication Systems and Network Technologies. ieeexplore.ieee.org/document/7058274.
[^EverydaySpeech2024]: *Everyday Speech in the Indian Subcontinent.* arXiv:2410.10508. Source for code-mixing as default register.
[^AddressTermsTelugu2016]: *The realization of address terms in Telugu in Andhra Pradesh.* allsubjectjournal.com — academic study of honorific/kinship address.

### Tier 2 — Vendor / official documentation

[^SarvamBulbul]: Sarvam AI. *Bulbul V3 model card.* sarvam.ai/blogs/bulbul-v3.
[^AI4BharatParlerTTS]: AI4Bharat. *Indic Parler-TTS model card.* huggingface.co/ai4bharat/indic-parler-tts.
[^AI4BharatIndicF5]: AI4Bharat. *IndicF5 model card.* huggingface.co/ai4bharat/IndicF5.
[^DeepgramAuraDocs]: Deepgram. *Voices and Languages — TTS.* developers.deepgram.com/docs/tts-models.
[^DeepgramSSMLStance]: Deepgram. *SSML support discussion.* github.com/orgs/deepgram/discussions/1031. Source for "moving away from SSML" position.
[^DeepgramAura2Expansion]: Deepgram. *Aura-2 Now Speaks Dutch, French, German, Italian, Japanese.* deepgram.com/learn/aura-2-now-speaks-dutch-french-german-italian-japanese. Note: no Indic on this expansion.

### Tier 3 — Industry / vendor blog (NOT normative)

[^TalkpalHonorifics]: Talkpal. *What are the honorifics used in Telugu and when should I use them?* talkpal.ai/culture. Source for Garu/Sri/Srimati/Vaaru — directional only; cross-checked with [^AddressTermsTelugu2016].
[^PipecatSarvamTTS]: Pipecat docs — Sarvam TTS integration. reference-server.pipecat.ai/en/stable/api/pipecat.services.sarvam.tts.html. Cited only as proof-of-existence.
[^BolnaSarvam]: Bolna docs — Sarvam voice provider. bolna.ai/docs/providers/voice/sarvam. Same.

### Implementation references

- Project memory: `parent_data_contract.md` — `language_preference` field on ParentRecord.
- Commit `3254a5a` — uniform Aura voice policy (Option C concern).
- ADR-017 (queued in goals charter) — DPDP Act compliance, related to vendor jurisdiction.
