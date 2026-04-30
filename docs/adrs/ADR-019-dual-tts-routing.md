# ADR-019: Plug-and-Play TTS Routing — Aura + Bulbul Per Language Preference

> **Date:** 2026-04-30
> **Status:** Accepted
> **Drives:** the dual-TTS work in DFS-010 §5 Option B; corrects the structural Telugu gap noted in DFS-010 §3.1.
> **Affects:** `src/infrastructure/{deepgram_tts_client,sarvam_tts_client,tts_router}.py`, `src/api/lifespan.py`, `src/infrastructure/production_pipeline.py`, env: `SARVAM_API_KEY`, optional `SARVAM_TELUGU_SPEAKER`.

## Context

The deployment serves two language-preference cohorts at Jaya High School:
- **English-preference parents** (e.g. `+918919230290` / Mr. Shiv Ram).
- **Telugu-preference parents** (e.g. `+919491116789` / Mrs. Lakshmi Devi).

Deepgram Aura — our incumbent TTS — does not support Telugu and has no SSML on its roadmap (DFS-010 §3.1). For Telugu-preference parents we either:
1. **Phonetically approximate** Telugu loanwords through Aura's English voice (DFS-010 Option A — already shipped in commits `a1d7887` + `c31930d`); bounded by what an American English voice can pronounce.
2. **Add a Telugu-native TTS** (DFS-010 Option B); uses Sarvam Bulbul v3, which supports Telugu (`te-IN`) as a first-class target with an explicit telephony-8 kHz benchmark.

This ADR accepts Option B. It does NOT replace Option A — Option A's loanword vocabulary remains useful for English-preference parents who happen to receive a Telugu honorific. Option B adds full-Telugu rendering for Telugu-preference parents.

## Decision

1. **Adopt Sarvam Bulbul v3 as the Telugu TTS provider.** Add `SarvamTTSClient` as a sibling adapter to `DeepgramTTSClient` under `src/infrastructure/`. Both adapters expose the same `synthesize(text, model=None, ssml=False) -> bytes` shape (returning WAV bytes) so they are substitutable behind a single port.

2. **Introduce `TTSRouter` as the runtime composition surface.** A small class that holds `default` plus an optional map `by_language: {lower-cased pref → adapter}`. Its public method is `synthesize(text, model=None, ssml=False, lang_pref="") -> bytes`. The router strips `lang_pref` before delegating to the chosen adapter — adapters never see the routing key.

3. **Routing is per-CALL, never mid-utterance.** Each TTS call is resolved against `lang_pref` once. The uniform-voice policy from commit `3254a5a` is preserved: a single agent voice per call. (DFS-010 Option C / sentence-level dual-TTS routing remains rejected.)

4. **Graceful fall-through.** If `SARVAM_API_KEY` is not configured or the adapter fails to construct, the router's Telugu route is `None` and Telugu-preference calls fall through to the default Aura adapter. The deployment never refuses a call due to Sarvam being unavailable.

5. **Pipeline thread-through.** `ProductionPipeline._synthesize_to_ulaw` accepts a new `session_id` kwarg. It looks up `lang_pref` via `EducationReceptionist.session_language_preference(session_id)` (a new typed accessor — replaces the LSP-smell `hasattr` introspection that DFS-009 §3.2 flagged for the parallel `session_has_record` case) and threads it into the router call.

## Configuration surface

| Env var | Default | Purpose |
|---|---|---|
| `SARVAM_API_KEY` | (unset) | Bulbul v3 API key. Unset = Aura-only (Telugu falls through to Aura). |
| `SARVAM_TELUGU_SPEAKER` | `gokul` | Bulbul v3 speaker for Telugu route. Valid values: see the Bulbul v3 speaker roster in `sarvam_tts_client.py` module docstring. |
| `DEEPGRAM_API_KEY` | (existing) | Aura TTS, English content. |

No infra changes required at the Container App level beyond env-var addition. The image already builds `src/infrastructure/sarvam_tts_client.py` because it ships under the same `src/` tree.

## Consequences

**Positive**
- Telugu-preference parents hear native-Telugu speech instead of phonetic-English approximation. Aligns with DFS-011 (Telangana register) and DFS-010 §2 (linguistic primitives that matter on the phone).
- Per-call provider choice is plug-and-play: future tenants in different regions can register `{"hindi": …, "tamil": …}` routes without touching the pipeline.
- Falls through gracefully — operational parity with Aura-only is preserved.
- Per-provider cost is opt-in (only Telugu calls hit Sarvam); no blanket migration.

**Negative**
- Two vendor dependencies → larger surface area for outages, billing complexity, and pricing drift.
- Voice timbre differs between English (Aura voice) and Telugu (Bulbul voice). Per-call uniformity preserves intra-call coherence; inter-call inconsistency is acceptable because each call is a single parent.
- Sarvam returns base64-encoded WAV that must be decoded; we already decode WAV in `_synthesize_to_ulaw` so the impact is the base64 step only.
- Latency profile of Sarvam vs Aura at our 24 kHz request rate is not yet measured on our actual telephony path. The DFS-010 §4 follow-up (`DFS-NN`) covers the measurement; this ADR is the architectural commitment that lets it happen.

**Mitigations**
- `routes_summary()` is logged at lifespan startup so misconfigurations (missing key, wrong speaker) are visible immediately.
- Adapter failures during construction are caught (`sarvam_tts_init_failed` warning event) with fall-through to the default; a Sarvam outage during call should appear as a per-call exception that the existing TTS error path handles.
- `lang_pref` lookup uses a public accessor (`session_language_preference`), not `hasattr` introspection, so adding a new receptionist subclass requires the developer to opt in explicitly.

## Alternatives Considered

1. **Stay Aura-only with Telugu loanwords (Option A only).** Adopted as a stopgap (commits `a1d7887`, `c31930d`); insufficient long-term for Telugu-preference parents wanting full Telugu sentences.
2. **Sentence-level dual-TTS (Option C from DFS-010).** Rejected — splits a single agent turn across two voices; conflicts with the uniform-voice policy from commit `3254a5a` ("two women and a man voice" feedback) and adds latency. Defer until Bulbul has demonstrated steady single-voice quality first.
3. **Per-tenant rather than per-call routing.** Tempting (cleaner architecturally), but a single Jaya HS deployment serves both English- and Telugu-preference parents from the same Twilio number; per-call routing is the necessary granularity.
4. **Self-host AI4Bharat IndicF5 / Indic Parler-TTS (BFS-006 §3.3 backup).** Strong open-source candidate; deferred behind a self-hosting infra ADR. Reachable via the same `TTSRouter` once an `IndicTTSClient` adapter is written.

## Verification (smoke-testable today)

- With `SARVAM_API_KEY` unset: routes_summary at startup shows `default=DeepgramTTSClient`, `by_language={}`. All calls route to Aura. (Existing behaviour, regression test.)
- With `SARVAM_API_KEY` set: routes_summary shows `default=DeepgramTTSClient`, `by_language={"telugu": "SarvamTTSClient"}`. Calls to `+918919230290` (Mr. Shiv Ram, English pref) route to Aura; calls to `+919491116789` (Mrs. Lakshmi Devi, Telugu pref) route to Bulbul. The greeting *"Namaskaaram Garu"* and the scenario opening *"Dhanyavaadalu for taking the call, Garu…"* are spoken by Bulbul's Telugu voice.

## References

- DFS-010 §3.1 (Aura's structural Telugu gap), §3.2 (Bulbul evaluation), §4 (architectural options), §5 (Option B as the right answer for full-Telugu).
- DFS-011 (Telangana register correction).
- BFS-006 §3.2 (Sarvam Saaras V3 STT) — sister BFS that suggests the same Indian-NLP vendor for the STT side; cross-cuts here.
- ADR-014 (Voice Intent Framework) — the receptionist's `language_preference` field comes from the verified ParentRecord that ADR-014 made first-class.
- DFS-009 §3.2 — the `hasattr` LSP smell this ADR's `session_language_preference` accessor avoids by following the same fix pattern.
