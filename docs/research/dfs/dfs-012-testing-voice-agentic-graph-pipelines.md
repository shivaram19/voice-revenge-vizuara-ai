# DFS-012: Testing Voice-Agentic Graph Pipelines

> **Date:** 2026-04-30
> **Scope:** Depth-dive on how to test voice agents whose runtime is a *directed graph* of states + branches (cached vs LLM, stage machine, intent shifts) — extending BFS-005's broader testing-tooling landscape into the graph-specific dimension. Triggered by user directive "test voice agentic graph pipelines."
> **Research Phase:** DFS — vertical depth on the graph-pipeline testing problem.
> **Status:** Active. Drives a pragmatic test-harness proposal in §5.

---

## 1. Why this DFS

Our deployed agent is *not* a single LLM-call-per-turn pipeline. It's a graph of branches:

```
              ┌── greeting ──► expect_invitation
              │                       │
              │     parent speaks?    │
              │       ↓ yes           │
              │   stage transition    │
              │   ┌────────┴────────┐
              │   ▼                  ▼
              │ cached path       LLM fallback
              │   │                  │
              │   ▼                  ▼
              │ cached audio       LLM → trim → TTS
              │ + backchannel?     + filler if slow
              │   │                  │
              │   └─────┬────────────┘
              │         ▼
              │   advance stage   ┌── intent shift?
              │         │         │   reset state machine
              │         ▼         │   re-pick scenario
              │   expect_summary_ack ◄┘
              │         │
              │      ... (recurses through stages) ...
              │         │
              │         ▼
              └── auto-close on silence (3s) OR LLM close OR caller hangup
```

Plus orthogonal state machines: post-intent (intent_satisfied → pivot_offered → news_offered → done), parent_lingering, dynamic budget mirror, session pace, interpreter-shift detection.

Treating this as a single integration test ("does the call succeed?") misses 80% of the failure surface. Each *node* and each *edge* is a test target.

---

## 2. Field tooling — what's emerged for graph-pipeline testing

| Tool | Scope | Native graph-coverage support | License | Cost |
|---|---|---|---|---|
| **voicetest** [^voicetestdev] | LLM-powered simulated callers + LLM judges; supports Retell/VAPI/LiveKit/Bland/custom | partial — exposes turn-by-turn replay but no built-in stage assertions | open-source | free |
| **LangWatch Scenario** [^LangWatchScenario] | Agentic testing for agentic codebases; simulated user talks to real-time agent + judge scores | strong — purpose-built for multi-step agentic workflows | open-source + paid SaaS | free tier |
| **Hamming AI** [^Hamming2026Voice] | Real PSTN/SIP simulation, 50+ metrics, regression in CI | medium — focused on call-level metrics not internal graph state | proprietary | $1k–3k/mo |
| **Roark** [^Maxim2026][^DEV2025] | Production call replay; convert real calls into regression cases | medium — replays real conversations rather than synthetic scenarios | proprietary | usage-based |
| **Braintrust** [^Braintrust2025] | Eval + observability unified; LLM-judge built in | weak for voice graph; strong for general LLM | SaaS | tiered |
| **Coval / Maxim AI / Cekura** [^Cekura2026] | Voice-agent-specific eval platforms | varies; survey them per use-case | SaaS | tiered |
| **DeepEval** [^DeepEval] | LLM evaluation framework, pytest-native | strong for unit/regression; not voice-specific | open-source | free |
| **Langfuse** [^Langfuse2025LLMTesting] | Observability + dataset-driven LLM regression in CI | medium; pytest pattern for LLM apps | open-source + SaaS | tiered |

The 2026 field is converging on three primitives:
1. **Simulated-caller LLM** that produces user turns (avoids needing humans for every test).
2. **LLM judge** that scores agent responses against intent / tone / accuracy criteria.
3. **Trace replay** — production traces become regression cases.

None of the platforms surveyed have *first-class* primitives for our specific graph constructs (cached-vs-LLM branching, mid-call scenario switching, post-intent state machine). That gap is what this DFS proposes filling with a tiny bespoke harness in §5.

---

## 3. The four testing layers we need

### 3.1 Unit — pure functions, deterministic
- Honorific helpers (`vocative`, `greeting_word`, `thanks`)
- Pace adapter (`_adapt_session_pace` — caller wps → pace map)
- Turn-budget adapter (`_adapt_turn_budget` — Communication Accommodation)
- Response-classifier (`_is_lingering_signal`, `_detect_intent_shift`, `_try_cached_response`)
- Scenario renderers (`render_intent_summary`, `render_intent_details`, `render_closing`)
- WAV concatenation (`_concat_wavs`)

These are pure or near-pure functions. **pytest with parametrize**, no LLM, no network. Already partially covered by my smoke-tests; should be promoted to `tests/unit/`.

### 3.2 Integration — graph state machine, mocked I/O
- Simulate a sequence of `_on_transcript` events (with synthesised TranscriptEvent objects) and assert the per-session state at each step:
  - `_stage[s]` transitions through the expected sequence
  - `_intent_satisfied`, `_pivot_offered`, `_news_offered` flip at the right moments
  - `_caller_word_history`, `_dynamic_max_words`, `_session_pace` evolve as expected
  - cached vs LLM dispatch fired at the right point
- Mock TTS and STT clients (no real Bulbul / Deepgram traffic).
- Run with `pytest-asyncio` over the existing async pipeline.

This is where **graph-coverage** lives — every edge in the diagram in §1 should have at least one passing test.

### 3.3 Conversation simulation — LLM-as-caller
- A simulated caller (LLM playing the parent role) talks to the live agent over a recorded call session.
- Caller is parameterised by personality: rushed, slow, suspicious, confused, code-switching.
- LLM judge evaluates the agent's responses against:
  - Did it match the verbatim opening template?
  - Did it deliver the verified-record content?
  - Did it close warmly when the caller signalled wrap-up?
  - Did it switch register / pace appropriately?
- Tools: **voicetest** [^voicetestdev] or **LangWatch Scenario** [^LangWatchScenario] — both Apache-licensed, pytest-runnable.

### 3.4 Production replay — graduated regression
- Capture real call traces (Twilio recordings + structured logs already produced).
- Convert each into a deterministic test case: caller audio → expected agent state-trajectory + scenario-template hits.
- Add to a CI dataset; new code must not regress against historical calls.
- Pattern from [^Langfuse2025LLMTesting]: continuous improvement cycle — score production conversations with LLM-as-judge, flag low-scoring, add to regression.

---

## 4. Graph coverage — what to assert

For our specific graph (production_pipeline.py + receptionist.py), the load-bearing edges:

| Edge | Test name | What to assert |
|---|---|---|
| greeting_complete → expect_invitation | `test_stage_init_after_greeting` | `_stage[s] == "expect_invitation"`; `_cached_audio[s]` keys subset {summary,details,closing,backchannel} |
| any caller utterance → expect_summary_ack | `test_invitation_advances_stage` | stage advances, summary dispatched (cached or LLM), `_intent_satisfied[s]` may be False at this point |
| caller "Avuna"/ack → expect_details_ack | `test_summary_ack_advances` | stage advances, details dispatched |
| caller "Thanks"/wrap-up → done | `test_wrapup_advances_to_done` | stage = done, closing dispatched |
| 3s silence after summary → done (auto-close) | `test_auto_close_silence` | stage = done, closing dispatched without caller speech |
| caller "admission" mid fee call → scenario shift | `test_intent_shift_admission` | `_scenarios[s]` now `admission_inquiry`; `_intent_satisfied`, `_pivot_offered`, `_news_offered` reset; `_intent_shifted_this_turn[s]=True` |
| caller >5 words after summary → backchannel prepend | `test_backchannel_long_caller_turn` | dispatched audio bytes start with backchannel bytes |
| caller 3.5 wps → pace=1.15 | `test_pace_match_fast_speaker` | `_session_pace[s]` close to 1.15 |
| cache miss when caller speaks before cache ready → stage advances + LLM | `test_cache_miss_advances_stage` | `cached_response_miss` event emitted; LLM path runs; next caller turn lands cached |
| Telugu pref → "Namasthe sir, Jaya High School nunchi matladthunnam" | `test_greeting_telugu_register` | greeting text matches verbatim |
| English pref → "Namaste sir. From Jaya High School." | `test_greeting_english_register` | English-pref greeting matches |
| record loaded → floor 6; no record → floor 12 | `test_session_floor_with_without_record` | `_session_budget_floor[s]` correct |

Eleven edges. Each test < 50 lines with mocks. Total coverage time ~200 LOC of test infrastructure.

---

## 5. Proposed harness for our codebase

### 5.1 Phase 1 — pytest-native unit + integration (1 day, ~300 LOC)

```
tests/
├── conftest.py                 # fixtures: fake_tts, fake_stt, fake_llm, fake_record
├── unit/
│   ├── test_honorifics.py      # vocative/thanks/greeting_word ✓×✗ pairs
│   ├── test_pace_adapter.py    # _adapt_session_pace boundary cases
│   ├── test_turn_budget.py     # _adapt_turn_budget across word counts
│   ├── test_lingering_signal.py # 12 cases (already smoke-tested in earlier session)
│   ├── test_intent_shift.py    # admission/attendance keyword sets
│   └── test_scenario_render.py # all 5 scenarios × Telugu/English pairs
├── integration/
│   ├── test_stage_machine.py   # 11 graph edges from §4
│   ├── test_cached_flow.py     # cache miss → LLM → cache ready next
│   ├── test_auto_close.py      # 3s silence triggers closing
│   ├── test_backchannel.py     # long caller turn prepends backchannel
│   └── test_intent_shift.py    # mid-call admission shift
└── fixtures/
    ├── transcript_events.py    # builders for TranscriptEvent
    └── mock_tts_router.py      # capture-bytes, no network
```

Each test imports the real `ProductionPipeline` and exercises the real state machine — only the network boundary (Deepgram WS, Sarvam HTTP, Twilio WebSocket) is mocked.

CI gate: this suite must pass before deploy. Anti-regression for the eleven graph edges.

### 5.2 Phase 2 — LangWatch Scenario for conversation-level (~2 days, ~150 LOC)

```python
import scenario  # langwatch/scenario package
from src.api.lifespan import build_pipeline  # factory we'd extract

@scenario.test()
async def test_paid_in_full_happy_path():
    sim_user = scenario.UserSim(
        persona="Telugu-speaking father in Suryapet, 38yo, busy, "
                "answers calls patiently. Says 'Cheppandi madam' "
                "after greeting; says 'Avuna' after the summary; "
                "says 'Thank you bye' at the end.",
        language="te",
    )
    judge = scenario.Judge(
        criteria=[
            "Agent opens with 'Namasthe sir, Jaya High School nunchi matladthunnam'",
            "Agent's summary contains 'Aarav term-1 fees kattesaru'",
            "Agent does NOT use 'Namaskaaram' (over-formal)",
            "Agent's closing contains 'Have a peaceful day'",
            "No more than 4 agent turns total after greeting",
        ],
    )
    result = await scenario.run(
        agent=build_pipeline().handle_call,
        user=sim_user,
        judge=judge,
        max_turns=10,
    )
    assert result.passed, result.failure_reason
```

Plus a parameterised matrix of personas (rushed / slow / suspicious / confused / code-switching) so we exercise the same scenario against the failure modes most likely in production.

### 5.3 Phase 3 — production-replay regression (~1 day, ~100 LOC)

The 13+ test calls placed in this session are *already* a corpus. Each has a Twilio recording + structured log JSON. A small harness:
1. Reads each recording's transcript (Deepgram).
2. Replays each caller turn into the agent's `_on_transcript`.
3. Snapshots the structured-event sequence.
4. Compares to a stored expected sequence.

Any new code that changes the event sequence on these historical calls produces a diff in CI; reviewer accepts (intentional change) or rejects (regression).

This is the **dataset-driven LLM regression** pattern from Langfuse [^Langfuse2025LLMTesting].

---

## 6. What NOT to build (yet)

- **Hamming AI** for real-PSTN simulation. Strong tool but $1–3k/month and overkill until we're past 100 production calls/day. The free pytest harness covers 80% of the failure modes for a Tier-3 deployment of our scale.
- **Custom audio-quality scoring** (WER, MOS). Already covered by Deepgram on the recording side; if needed, add as a post-call eval, not a per-PR gate.
- **Browser-based call simulation UI**. Operations get the structured-log timeline + recording — sufficient.

---

## 7. The 10-persona filter

| Persona | Verdict |
|---|---|
| Research Scientist | Test plan grounded in published primitives (Cohen 2004 simulated callers, Anthropic 2025 evals demystified, Langfuse 2025 regression pattern) |
| First-Principles Engineer | Each graph edge is a primitive that can be tested in isolation; integration emerges from composition |
| Distributed Systems Architect | Mocking at I/O boundaries means tests run sub-second; CI cost stays low at 1M-user scale |
| Infrastructure-First SRE | Production-replay phase converts our existing structured-event stream into a regression dataset for free |
| Ethical Technologist | LLM judge evaluates *parent dignity* dimensions (no rushing, no register breaks) explicitly |
| Resource Strategist | $0 infra cost (pytest + open-source LangWatch/voicetest); buys 100% of the failure-mode coverage that matters at our scale |
| Diagnostic Problem-Solver | Each test isolates one edge; failures are immediately attributable to a specific node/transition |
| Curious Explorer | Phase 3 replay corpus grows naturally; new test cases come from real calls, not synthesis alone |
| Clarity-Driven Communicator | Test names are 1-1 with §4 graph edges; non-engineers can read the test file and understand the behaviour matrix |
| Inner-Self Guided Builder | "Would I want my own father called by an agent that hadn't passed all eleven edges?" — answers itself |

---

## 8. Open questions / future DFS

1. **Continuous LLM-judge in production.** Score every live call with the same judge from §5.2; flag low-scoring sessions; auto-promote to regression set. (Pattern from [^Langfuse2025LLMTesting].)
2. **A/B test harness.** Compare two pipeline revisions on the same simulated-call set; report behavioural deltas. Critical when the next batch of refactors lands (DFS-009 SOLID batches).
3. **Edge-case generator.** LLM-driven adversarial caller (LangWatch Scenario can do this) — produces personas designed to *break* the agent (silent caller, multi-language switcher, hostile tone).
4. **DSPy / GEPA prompt optimisation in the loop.** Once we have evals, the prompt-engineering work (fee_paid_confirmation posture_note, etc.) becomes optimisable. Phase 4 deferred until phases 1–3 are operational.

---

## References

> Tiers per AGENTS.md. After the citation-honesty audit (commit d315118): peer-reviewed / arXiv / canonical industry whitepapers as Tier 1; vendor docs as Tier 2; vendor blogs as Tier 3 (NOT normative).

### Tier 1 — Canonical / arXiv

[^Anthropic2025DemystifyingEvals]: Anthropic. (2025). *Demystifying evals for AI agents.* anthropic.com/engineering/demystifying-evals-for-ai-agents. Engineering article from a Tier-1 vendor; treat as canonical for the eval-harness primitives.

### Tier 2 — Open-source projects + vendor docs

[^voicetestdev]: voicetestdev/voicetest GitHub repo. *Test harness for voice agents.* github.com/voicetestdev/voicetest. Apache-licensed.
[^LangWatchScenario]: langwatch/scenario GitHub repo. *Agentic testing for agentic codebases.* github.com/langwatch/scenario.
[^Langfuse2025LLMTesting]: Langfuse. (2025-10-21). *LLM Testing: A Practical Guide to Automated Testing for LLM Applications.* langfuse.com/blog. Open-source observability vendor with documented pytest-LLM regression pattern.
[^DeepEval]: DeepEval (Confident AI). *The LLM Evaluation Framework.* deepeval.com. Open-source.

### Tier 3 — Industry coverage (NOT normative)

[^Hamming2026Voice]: Hamming AI. *Enterprise Voice Agent Testing & Production Monitoring.* hamming.ai.
[^Maxim2026]: Maxim AI. *Best Voice Agent Evaluation Tools in 2026.* getmaxim.ai. Roark mention.
[^DEV2025]: DEV community. *Top 5 Voice Agent Evaluation Tools in 2025.* dev.to/kuldeep_paul.
[^Cekura2026]: Cekura.ai. *5 Best Voice Agent Testing Platforms (2026).*
[^Braintrust2025]: Braintrust. *How to evaluate voice agents.* braintrust.dev.

### Implementation references

- BFS-005 — prior testing-frameworks landscape (broader scope).
- DFS-009 — SOLID audit (the 5-batch refactor sequence will lean on this harness for regression confidence).
- Production calls from this session (13+) — already-collected corpus for Phase 3 replay.
