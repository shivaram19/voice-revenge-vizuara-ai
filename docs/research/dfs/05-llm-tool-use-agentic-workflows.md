# DFS-05: LLM Reasoning, Tool Use & Agentic Workflows

**Research Phase**: DFS traversal from LLM Brain node  
**Scope**: Function calling, ReAct, memory integration, prompt engineering for voice  
**Date**: 2026-04-25

---

## Why ASR + TTS Alone Is Not Enough

A voice agent with only ASR and TTS is a **talking search engine**. It can transcribe and speak, but it cannot:
- Look up your calendar
- Search the web
- Calculate complex expressions
- Remember preferences across sessions
- Take actions in external systems

The LLM is the **reasoning and decision-making layer** that transforms speech recognition into agency.

---

## Reasoning Paradigms

### Paradigm 1: Direct Generation (Baseline)
**Method**: LLM receives transcript + context → generates response.
**Pros**: Simple, fast, no external dependencies.
**Cons**: Hallucinates facts; cannot access real-time data; no action capability.

### Paradigm 2: Function Calling (Recommended for Voice)
**Method**: LLM decides whether to call a function; application executes; result fed back.
**Flow**:
```
User: "What's the weather in Seattle?"
LLM: function_call(name="get_weather", args={"location": "Seattle"})
App:  result = get_weather("Seattle")  # API call
LLM:  "It's 62°F and cloudy in Seattle."
```
**Pros**: Deterministic, fast, reliable for known operations.
**Cons**: Cannot handle ambiguous requests requiring exploration.

**Latency impact**: One tool call adds ~500ms-2s (API round-trip). For voice, this must be masked with filler audio ("Let me check that...").

**Citation**: OpenAI Function Calling API [^13]; Yao et al. (2023) [^74].

### Paradigm 3: ReAct (Reason + Act)
**Method**: LLM iterates through thought → action → observation loops.
**Flow**:
```
Thought: I need to check the weather in Seattle.
Action: get_weather(location="Seattle")
Observation: {"temp": 62, "condition": "cloudy"}
Thought: I have the information. I can now answer.
Response: "It's 62°F and cloudy in Seattle."
```
**Pros**: Handles multi-step reasoning; self-correcting; transparent.
**Cons**: 2-4× more tokens than function calling; higher latency; unsuitable for real-time voice without optimization.

**Citation**: Yao et al. (2023), "ReAct: Synergizing Reasoning and Acting in Language Models" [^74].

---

## Hybrid Strategy for Voice

**Recommendation**: Use **function calling as default**, **ReAct for complex research tasks**.

**Router pattern**:
```python
if query_complexity_score < 0.7:
    return function_calling_agent(query)
else:
    return react_agent(query)  # with user notification of delay
```

**Citation**: Tezeract.ai (2026) hybrid analysis [^74].

---

## Prompt Engineering for Voice

Voice agents require fundamentally different prompting than text chatbots.

### Principle 1: Conciseness
Text LLMs are trained on essays. Voice requires **telegraphic responses**.

**Bad**: "The weather in Seattle, Washington, United States, as of 2:15 PM Pacific Daylight Time on April 25th, 2026, is 62 degrees Fahrenheit with cloudy conditions and a 20% chance of precipitation in the evening."

**Good**: "It's 62 and cloudy in Seattle. Might rain later."

### Principle 2: Spoken-Style Disfluency
Humans say "um" and "ah." Voice agents do not use disfluency. Voice agents use natural fillers for latency masking, a pattern validated in production streaming pipelines where filler audio reduces perceived latency by 200-400ms during tool execution [^16].

**Latency masking phrases**:
- "Let me check..."
- "One moment..."
- "Looking that up..."

These are generated and spoken *while* the tool executes, making the delay feel natural.

### Principle 3: Interruption-Friendliness
Design prompts so responses can be truncated mid-sentence without losing critical information.

**Structure**: [Key answer] + [Elaboration] + [Action item]
- If interrupted after key answer: user got what they needed.
- If interrupted during elaboration: no harm done.

---

## Conversation History Management

### The Context Window Problem
LLMs have finite context windows. A 10-minute conversation at 150 WPM = 1,500 words ≈ 2,000 tokens. At 20 turns, this fills most 4K-8K context windows.

### Strategies

#### Strategy 1: Sliding Window
Keep last N turns (e.g., 6). Drop older turns.
**Pros**: Simple, predictable token count.
**Cons**: Loses early conversation context.

#### Strategy 2: Hierarchical Summarization
Every 4 turns, summarize to 1 paragraph. Store summary + last 2 raw turns.
**Pros**: Preserves gist indefinitely.
**Cons**: Loses specific details; summary latency.

#### Strategy 3: Selective Retention (Recommended)
Use LLM to classify each turn:
- **CRITICAL**: Facts, preferences, commitments — always keep.
- **TRANSIENT**: Greetings, filler — summarize or drop.
- **ACTION**: Tool calls and results — keep until confirmed.

**Citation**: This approach is informed by VoiceAgentRAG conversation stream management [^14].

---

## Tool Design for Voice

### Constraints
1. **Timeout**: Tools must complete in <2s or return async handle.
2. **Idempotency**: Same tool call with same idempotency key = same result.
3. **Safety**: All tool inputs/outputs logged and PII-redacted.
4. **Fallback**: If tool fails, LLM must generate graceful degradation.

### Example Tool Schema
```json
{
  "name": "schedule_meeting",
  "description": "Schedule a calendar meeting. Confirm with user before executing.",
  "parameters": {
    "title": {"type": "string"},
    "start_time": {"type": "string", "format": "iso8601"},
    "duration_minutes": {"type": "integer", "default": 30},
    "attendees": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["title", "start_time"],
  "voice_confirmation": true
}
```

**Key**: `voice_confirmation: true` — the agent must verbally confirm before mutating state.

---

## References
[^13]: OpenAI. (2023). Function Calling API Documentation.
[^14]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^16]: SigArch. (2026). Section 4.5. Filler audio and latency masking in production streaming TTS pipelines. *arXiv:2603.05413*.
[^74]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR*.
[^74]: Tezeract.ai. (2026). ReAct vs Function Calling Agents.

[^1]: OpenAI. (2023). Function Calling API Documentation.
[^2]: Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR*.
[^3]: Tezeract.ai. (2026). ReAct vs Function Calling Agents.
[^4]: Qiu, J., et al. (2026). VoiceAgentRAG. *arXiv:2603.02206*.
[^5]: SigArch. (2026). Section 4.5. Filler audio and latency masking in production streaming TTS pipelines. *arXiv:2603.05413*.
