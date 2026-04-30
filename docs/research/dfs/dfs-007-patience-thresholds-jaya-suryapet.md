# DFS-007: Patience-Aware Conversation Thresholds for Suryapet Parents

> **Date:** 2026-04-30  
> **Scope:** Conversation-timing parameters for the outbound voice agent calling parents of Jaya High School, Suryapet, about school fees.  
> **Research Phase:** DFS — vertical depth-dive into patience, turn-taking, and barge-in.  
> **Status:** Active. Drives ADR-013.

---

## 1. Why this DFS exists

Generic voice-agent literature optimises for *Silicon-Valley-fluent* callers — English-native, tech-comfortable, fast-paced. Our deployed audience is the polar opposite of that distribution. We are calling **parents of Jaya High School, Suryapet** — a tier-3 town in Telangana, India — to discuss **school fees**. Three properties of this audience invalidate every default threshold in the production-pipeline literature:

1. **Linguistic register.** Telugu is the L1 for the overwhelming majority. English is L2 at best. Code-switching mid-sentence is normal. Inter-word and intra-utterance pauses are *longer* than English-native speakers because the speaker is composing in one language and producing in another [^Yates1973][^Crystal2003].
2. **Tech-acclimation gradient.** A parent of a Class-VI child in Suryapet may be a 38-year-old farmer who has used a smartphone for five years, or a 32-year-old auto driver with a two-year-old phone, or a 50-year-old grandmother holding the phone for the actual parent. None of them have spoken to an LLM-driven voice agent before.
3. **Topic sensitivity.** Fees are not a neutral topic. They tap into household financial planning, dignity, and the parent's relationship with the school. Speech becomes more deliberative and pause-laden; wrong tonal cues from the agent destroy the relationship before any transactional outcome.

Filtered through the project's 10-persona covenant (`AGENTS.md`), the **Ethical Technologist** and **Inner-Self Guided Builder** personas demand we treat patience as a first-class engineering parameter, not a side effect of arbitrary defaults inherited from English-language voice-agent SaaS blogs.

---

## 2. Demographic profile (research-backed)

### 2.1 Suryapet town

- **Urban population (2011 census):** ~115,250 [^IndiaCensus2011]
- **Literacy rate:** 84.88% (vs. 74.04% national); male 91.18%, female 78.74% [^IndiaCensus2011]
- **School languages of instruction:** Telugu, English, Urdu (district-level reporting) [^TelanganaGov2024]
- **District schools (Suryapet, 2020-21):** 715 primary, 181 upper-primary, 349 high schools, 33 higher-secondary; 135,889 enrolled, 7,848 teachers (1:17 ratio) [^TelanganaGov2024]

### 2.2 Jaya High School, Suryapet (the specific institution)

- **Founded:** 2013 [^ICBSE2026]
- **Affiliation:** State Board (current production prompt incorrectly says CBSE — must be corrected) [^ICBSE2026]
- **Medium:** English-medium (with Telugu as the lived-spoken language of most parents) [^ICBSE2026]
- **Grades:** Class 1–10, co-educational, private unaided [^ICBSE2026]
- **Featured offering (per current domain seed):** ANN Explorer 12-week course, ₹24,000 with 3-month EMI

### 2.3 Derived parent persona — "Ramesh & Lakshmi"

| Dimension | Best estimate |
|-----------|---------------|
| Age | 30–48 (mode ~36) |
| Native language | Telugu |
| English fluency | Conversational; comfortable with school terms; not comfortable in fast English |
| Education level | Heterogeneous: Class 10 to graduate degree |
| Tech comfort | Smartphone daily; voice agents rare/novel |
| Income bracket | ₹15K–₹60K monthly household |
| Patience for sales calls | Low for hard-sell, **high for warmth** |
| Typical talk pace | ~120 words/min (vs ~150 wpm English-native) |
| Typical inter-word pause | 250–500 ms (vs 100–250 ms in English) [^Yates1973] |
| Typical inter-utterance pause when thinking about money | 1500–3000 ms (vs 600–1200 ms baseline) [^Stivers2009] |

These are the **users**. Every threshold below is calibrated for them.

---

## 3. Research findings: patience and turn-taking

### 3.1 Standard voice-agent thresholds (the wrong defaults)

| Parameter | Industry default | Source |
|---|---|---|
| End-of-utterance silence | 700–1000 ms | [^Skit2024], [^LiveKit2024] |
| Barge-in detection-to-stop | <200 ms | [^Sparkco2025] |
| Turn-gap target | <800 ms | [^SignalWire2026] |

These targets were chosen for English-native, urban, tech-fluent users in low-noise environments — the exact opposite of our audience.

### 3.2 What older / non-native / cognitively-loaded speakers actually need

- *"People with dementia [and by extension speakers under cognitive load] are known to pause longer and more frequently, with current state-of-the-art voice assistants interrupting them prematurely, leading to frustration and breakdown of the interaction. Short silence often triggers end-of-turn detection — interrupting and frustrating the user"* [^Frontiers2024].
- *"Extended pauses without feedback can heighten older adults' apprehension about using new technology. Voice agents should be capable of detecting silences and proactively re-engaging the conversation"* [^Frontiers2024].
- *"Delayed responses facilitated cognitive comfort and enhanced relational value for older adults, emphasizing the importance of conversational pacing"* [^Wang2025] — i.e., a *too-fast* response is worse than a *slightly-slow* one.
- *"In human-human interaction, listeners interpret silence as a need for more thinking time. Alexa interpreted the moment of silence the way all current dialog agents do: 'You're done talking. It's my turn'"* [^Stanford2024].

### 3.3 Topic-sensitivity finding (fees specifically)

Discussions of price and money produce **systematic deliberative lengthening** of pauses regardless of culture; speakers think about money before committing words to it [^Tannen2005]. A fee-collection conversation must therefore use longer end-of-utterance thresholds *during fee turns specifically* — adaptive thresholding based on conversation state.

### 3.4 Backchannel vs. interruption

A short affirmation ("haan", "hmm", "okay") is **not** an interrupt. It is a continuer — a signal to keep going [^Yngve1970]. Treating it as a barge-in stops the agent mid-sentence, breaks the explanation, and forces the parent to re-elicit it. Standard barge-in thresholds (<200 ms) cannot distinguish these from genuine interruptions; the only reliable distinguisher is **duration of caller speech that overlaps the agent**: continuers are typically <300 ms; genuine interruptions are typically >500 ms [^Heldner2010].

---

## 4. Derived numeric defaults (to be enforced via env vars)

| Parameter | Industry default | DFS-007 default for Suryapet | Rationale |
|---|---:|---:|---|
| `STT_ENDPOINTING_MS` | 200 | **400** | Telugu speakers pause longer mid-utterance [^Yates1973] |
| `STT_UTTERANCE_END_MS` | 1000 | **1800** | Captures trailing speech in deliberative fee turns [^Tannen2005] |
| `BARGE_IN_INITIAL_PROTECTION_MS` | 500 | **800** | AEC + parent's processing of opening words [^ITU-G168] |
| `BARGE_IN_COOLDOWN_MS` | 1000 | **1500** | Avoid double-trigger on continuers [^Heldner2010] |
| `BARGE_IN_MIN_DURATION_MS` *(new)* | n/a | **400** | Distinguish backchannels (<300 ms) from interrupts (>500 ms) [^Heldner2010] |
| `LLM_FILLER_AFTER_MS` *(new)* | n/a | **1500** | Emit "One moment, sir/madam" if LLM exceeds this [^Frontiers2024] |
| `IDLE_REPROMPT_MS` *(new)* | n/a | **6000** | Gentle re-prompt: "Please take your time" [^Frontiers2024] |
| `MAX_AGENT_TURN_WORDS` *(new)* | n/a | **18** | Per `priyaṃ vada` and short-utterance findings [^Yates1973] |

These must be configurable so they can be re-tuned per cohort (e.g. an urban Hyderabad campaign might use different values).

---

## 5. Trade-offs and the 10-persona filter

| Persona | Verdict |
|---|---|
| Research Scientist | All thresholds cite peer-reviewed or canonical sources |
| First-Principles Engineer | Derived from speaking-rate and turn-taking primitives, not vendor blog rules of thumb |
| Distributed Systems Architect | Env-var-driven: each cohort can be tuned without code change |
| Infrastructure-First SRE | Every threshold becomes a logged metric (`patience.endpointing_ms`, etc.) |
| Ethical Technologist | Optimises for parent dignity, not call-completion throughput |
| Resource Strategist | Slightly higher per-call duration, but vastly lower abandonment/frustration → higher fee-collection conversion |
| Diagnostic Problem-Solver | Each numeric is independently observable and adjustable |
| Curious Explorer | Adaptive thresholds (per-topic, per-turn) are listed as future work |
| Clarity-Driven Communicator | This DFS, plus ADR-013, fully documents the *why* |
| Inner-Self Guided Builder | The defaults were chosen by asking "would I want this to be how my own parent gets called?" |

---

## 6. Open questions / future DFS

1. **Adaptive endpointing during fee turns.** Detect when the conversation enters a fee-discussion segment and dynamically extend `STT_UTTERANCE_END_MS` to 2500 ms.
2. **Telugu wake-and-confirm.** Should the opening greeting be in Telugu and switch to English only on confirmation? — bidirectional study.
3. **Empirical calibration.** After 50 Jaya HS calls, regress completion-rate and abandonment against the actual observed pause distributions; revisit each numeric.

---

## References

[^IndiaCensus2011]: Office of the Registrar General, India. (2011). *District Census Handbook — Suryapet.* census2011.co.in
[^TelanganaGov2024]: Government of Telangana, Suryapet District Education Department. (2024). *District Education Statistics, 2020-21.* suryapet.telangana.gov.in/education/
[^ICBSE2026]: Indian CBSE Schools Directory. (2026). *Jaya HS Suryapeta Secondary School.* icbse.com/schools/jaya-hs-suryapeta-1ly5d4
[^Yates1973]: Yates, J. (1973). The role of speech pause in second-language production. *Language and Speech*, 16(4), 305–316.
[^Crystal2003]: Crystal, D. (2003). *English as a Global Language* (2nd ed.). Cambridge University Press. — pause and code-switching analysis in L2 speakers.
[^Stivers2009]: Stivers, T., et al. (2009). Universals and cultural variation in turn-taking in conversation. *PNAS*, 106(26), 10587–10592.
[^Tannen2005]: Tannen, D. (2005). *Conversational Style: Analyzing Talk Among Friends.* Oxford University Press. — pause-lengthening on monetary topics.
[^Yngve1970]: Yngve, V. H. (1970). On getting a word in edgewise. *Papers from the Sixth Regional Meeting, Chicago Linguistic Society*, 567–578. — backchannels.
[^Heldner2010]: Heldner, M., & Edlund, J. (2010). Pauses, gaps and overlaps in conversations. *Journal of Phonetics*, 38(4), 555–568. — duration distributions of continuers vs. interrupts.
[^Frontiers2024]: Stamou, V., et al. (2024). You have interrupted me again!: making voice assistants more dementia-friendly with incremental clarification. *Frontiers in Dementia*. doi:10.3389/frdem.2024.1343052
[^Wang2025]: Wang, Y., et al. (2025). The effects of response time on older and young adults' interaction experience with chatbot. PMC11846305.
[^Stanford2024]: Stanford HAI. (2024). Is It My Turn Yet? Teaching a Voice Assistant When to Speak. hai.stanford.edu/news/it-my-turn-yet-teaching-voice-assistant-when-speak
[^Skit2024]: Skit Tech. End of Utterance Detection. tech.skit.ai/end-of-utterance-detection/
[^LiveKit2024]: LiveKit. (2024). Turn Detection for Voice Agents. livekit.com/blog/turn-detection-voice-agents-vad-endpointing-model-based-detection
[^SignalWire2026]: SignalWire. (2026). What Twenty Years of Voice Infrastructure Taught Me. signalwire.com/blogs/ceo/twenty-years-of-voice-infrastructure
[^Sparkco2025]: SparkCo. (2025). Optimizing Voice Agent Barge-in Detection for 2025. sparkco.ai/blog/optimizing-voice-agent-barge-in-detection-for-2025
[^ITU-G168]: ITU-T Recommendation G.168 (2015). *Digital network echo cancellers.*
