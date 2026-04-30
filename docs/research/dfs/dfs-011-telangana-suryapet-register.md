# DFS-011: Telangana / Suryapet Telugu Speech Register — Correcting the Generic-Telugu Drift

> **Date:** 2026-04-30
> **Scope:** The Telugu honorifics shipped in commit `a1d7887` (DFS-010 Option A) used *generic Telugu* register, not the *Telangana register* that Suryapet parents actually speak. This DFS corrects the drift, documents what the regional difference is, and constrains future TTS / prompt work to the right register.
> **Research Phase:** DFS — depth-dive into a known cultural gap.
> **Status:** Active. Drives a small revision to `src/tenants/jaya_high_school/honorifics.py` and the education system prompt.

---

## 1. The error this DFS corrects

DFS-010 §2.2 prescribed `Garu` honorific suffix and `Dhanyavaadalu` close. Both are *correct Telugu*, but they're the **Andhra / formal-textbook** register. Our entire deployed audience lives in **Suryapet, Telangana** — a rural-Telangana town that speaks the **Telangana dialect**, which differs from Andhra Telugu in three load-bearing ways:

1. Hyderabadi-Urdu vocabulary influence from 224 years of Nizam rule (1724–1948) [^TelanganaDialectWiki].
2. Softer, more nasal phonology vs Andhra's crisp register [^Talkpal2024TelanganaVsAndhra].
3. Different greeting / politeness conventions on the phone — `Namaskaaram` is the Telangana-preferred formal greeting, `Namaste` is the pan-Indian/Hindi-influenced shorter form [^Preply2024TeluguGreetings].

Calling a Suryapet parent with Andhra-textbook Telugu is not *wrong* — they will understand it — but it sounds like a Hyderabad-corporate marketer rather than a school they trust. The prosodic mismatch is a credibility cost.

---

## 2. What changes (concrete)

| Surface | Before (DFS-010) | After (DFS-011) | Why |
|---|---|---|---|
| Greeting (Telugu-pref) | `Namaste Garu` | `Namaskaaram Garu` | `Namaskaaram` is the formal Telugu greeting; `Namaste` is Hindi/Sanskrit register [^Preply2024TeluguGreetings] |
| Greeting (English-pref) | `Namaste sir` | unchanged | English-pref parents tolerate either; keep current |
| Closing thanks (Telugu-pref) | `Dhanyavaadalu, Garu` | unchanged | `Dhanyavaadalu` works in Telangana register, just slightly formal |
| Verb register guidance to LLM | absent | new prompt rule | LLM now informed Suryapet parents prefer honorific-verb-ending register (`chEsāru` / `unnāru` / `vaccāru`) — applies to any Telugu phrase the LLM emits |
| Honorific name form | `Mrs. Lakshmi Devi Garu` | unchanged | Garu is universal across Telugu varieties |

The change-set is intentionally small. Only one user-facing string is altered. The rest is informational — the LLM's system prompt now carries the *demographic context* so its dynamic mid-call replies match the register without us hard-coding more phrases.

---

## 3. What we deliberately do NOT change

Five tempting Telangana-isms that we evaluated and **rejected** for production today, with reasons:

### 3.1 `Bagunnara?` ("are you well?") at the start of the call
Authentic Telangana phone-call register; almost any local school administrator would open with this. **Rejected** because:
- Aura's American/British English voices cannot phonetically render `Bagunnara` (`ba-GOO-nuh-rah`) without it sounding like nonsense to a native speaker. Worse-than-not-saying-it.
- Adding it requires the dual-TTS path in DFS-010 §4 Option B, which is queued behind a Sarvam Bulbul DFS-NN. Until Bulbul lands, faking it through Aura damages trust more than its absence.

### 3.2 `Saar` / `Annaa` / `Akka` (informal kinship honorifics)
Common in rural Telangana — `Saar` is the colloquial English-loanword "sir"; `Annaa` (elder brother) and `Akka` (elder sister) are warm address forms used even with non-relatives. **Rejected** because:
- These are *informal* register; a fee-collection call is NOT a friendship call. Using `Annaa` in this context would feel intrusive — the school is not the parent's brother [^TalkpalTeluguChildVsAdult].
- A school's official voice should be respectful-formal, not familial. The `Garu` form preserves respect without faking intimacy.

### 3.3 Hyderabadi-Urdu loanwords (`khabar`, `sahab`, `pareshaani`)
Genuinely part of Telangana daily speech [^TelanganaDialectWiki]. **Rejected today** because:
- These are Hyderabad-urban register more than rural-Telangana register; Suryapet leans Hindu-Telugu rather than Hyderabadi-Muslim cultural orbit, and Urdu loanwords are less load-bearing in rural contexts.
- We have no calibration data on how Suryapet parents specifically respond to Urdu-flavoured speech from a school. Deferred until we've placed real production calls and can A/B.

### 3.4 Honorific verb conjugation (`chEsāru`, `vaccāru`)
Telugu marks respect *grammatically* via verb endings — `chEsādu` (he did, plain) vs `chEsāru` (they did, honorific singular) [^Preply2024TeluguGreetings]. **Cannot be implemented in our current architecture** because the LLM speaks English; the construct doesn't translate. Captured in the prompt as *contextual awareness for the LLM*, not as a code change.

### 3.5 Suprabhatam (morning greeting)
The traditional formal morning greeting. **Rejected** because:
- Time-of-day-aware greetings require a clock dependency in the receptionist that's currently absent.
- Most fee-reminder calls happen in late-afternoon school hours per project memory; `Suprabhatam` would be wrong most of the time. Deferred behind a clean clock injection.

---

## 4. The principle this DFS establishes

**Match the regional register, not the language family.**

A naive "speak Telugu to Telugu-preference parents" implementation drifts toward generic / textbook Telugu — Sanskrit-derived vocabulary, Andhra-formal prosody — because that's what Telugu language resources on the internet teach. Our parents do not speak generic Telugu. They speak Telangana Telugu; specifically rural-Suryapet Telangana, with low-Hyderabadi-Urdu influence.

The principle: when adding language support, **filter through both axes** — language *and* region. The `ParentRecord.language_preference` field is currently a coarse `English | Telugu` tag; a future revision should expand it to `language: Telugu, region: Telangana_Rural` so a tenant in Vijayawada (Andhra) and a tenant in Suryapet (Telangana) both serving Telugu speakers can route to different register lexicons.

This is **not** a code change for today. It is a constraint on every future tenant onboarding (ADR-018) and on the dual-TTS work (DFS-010 Option B / DFS-NN).

---

## 5. The 10-persona filter on this revision

| Persona | Verdict |
|---|---|
| Research Scientist | Tier 1 source for Telangana dialect (Wikipedia article cites Nizam-period contact + linguistic studies); Tier 2 for greeting register (Preply / Talkpal — culture/language-learning sites, treated as directional). |
| First-Principles Engineer | Derived from the linguistic primitive (regional dialect ≠ language); not from "what other voice agents do". |
| Distributed Systems Architect | Trivially scales: small string change + prompt-rule addition; no infra impact. |
| Infrastructure-First SRE | No new metrics needed; existing call-quality telemetry covers register-fit if we ever A/B. |
| Ethical Technologist | Net positive — using Telangana-correct register dignifies the parent. |
| Resource Strategist | Zero TCO impact. |
| Diagnostic Problem-Solver | Root cause was using *Telugu* tag without distinguishing region. Fix at the principle level (§4), not just the symptom. |
| Curious Explorer | Five rejected register options documented in §3 with reasons — explicitly preserves the lab notebook for future revisits. |
| Clarity-Driven Communicator | This DFS + the 1-line code change + the prompt-rule addition = full provenance. |
| Inner-Self Guided Builder | The Suryapet parent answering this call would notice `Namaskaaram Garu` is the right form. That's enough. |

---

## 6. Future work explicitly queued

1. **DFS-NN: Suryapet rural-register A/B.** After ≥50 production calls with `Namaskaaram` greeting, measure parent-reported warmth / trust against a held-out cohort still receiving the (legacy) `Namaste`. Honest empirical validation; the hypothesis here is plausible but not yet measured.
2. **`ParentRecord.region` field.** Coarse `language_preference` is a stopgap; production needs a `(language, region)` pair so per-region register lexicons can register cleanly. Captured as a goals-charter item under §6 BFS / DFS open questions.
3. **Dual-TTS register expansion (DFS-010 Option B).** Once Sarvam Bulbul or AI4Bharat IndicF5 is live, the *full* Telangana-register lexicon (Bagunnara, honorific verb conjugation, kinship-respect endings) becomes pronounceable and the §3 rejected items can be revisited.
4. **Time-of-day-aware greeting.** `Suprabhatam` for morning, `Namaskaaram` for afternoon, `Subhasandhya` for evening. Behind a clock-injection refactor.

---

## References

> Tiers per AGENTS.md: Tier 1 = peer-reviewed / canonical; Tier 2 = vendor docs / public data; Tier 3 = industry coverage (NOT normative).

### Tier 1 — Canonical / academic

[^TelanganaDialectWiki]: Wikipedia. *Telangana dialect.* en.wikipedia.org/wiki/Telangana_dialect. Cited for the Nizam-period (1724–1948) Hyderabadi-Urdu contact, phonological softness vs Andhra crispness, and lexical examples (`nīru` vs `nīṭi`, `ḍabbulu`, `bābāy`).

### Tier 2 — Public-data / language-learning resources

[^Preply2024TeluguGreetings]: Preply. *Essential Telugu Greetings for Every Occasion.* preply.com/en/blog/telugu-greetings-for-every-occasion/. Cited for `Namaskaaram` formal-vs `Namaste` informal distinction and honorific-verb-ending convention (`chEsāru` / `unnāru`).
[^Talkpal2024TelanganaVsAndhra]: Talkpal. *What is the difference between Telangana and Andhra dialects of Telugu?* talkpal.ai/culture. Cited for prosodic / phonological difference; treated as directional Tier-2 (language-learning content, not peer-reviewed linguistics).
[^TalkpalTeluguChildVsAdult]: Talkpal. *What is the difference between speaking Telugu to a child versus an adult?* talkpal.ai/culture. Cited for the formality-vs-intimacy axis used in §3.2 reasoning.

### Implementation references

- Project memory: `parent_data_contract.md` — `language_preference` field on ParentRecord.
- Commit `a1d7887` — DFS-010 Option A (Telugu honorifics) — the work this DFS corrects.
- Commit `9eb4f3e` — DFS-010 (Telugu prosody) — the parent research this DFS extends.
- ADR-018 (queued) — Tenant onboarding playbook (where the `(language, region)` pair belongs).
