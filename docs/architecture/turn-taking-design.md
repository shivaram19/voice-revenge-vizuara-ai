# Turn-Taking Design
## "Only When You're Ready to Give Attention, Only Then You'll Be Attended To"

> **Principle:** The AI does not speak because it CAN. The AI speaks because it is INVITED.  
> **Metaphor:** The AI is a guest in the user's home. It waits to be offered a seat. It does not sit uninvited. It does not speak until spoken to. It does not overstay.

---

## The Problem with Current Voice AI

Most voice agents violate the basic etiquette of human conversation:

| Violation | What Humans Do | What Bad AI Does |
|-----------|---------------|------------------|
| **Interruption** | Wait for silence + invitation | Speaks as soon as STT returns text |
| **Barge-in ignorance** | Stop immediately when interrupted | Finishes its sentence over the user |
| **Monologuing** | Speak in chunks, check for understanding | Streams 30 seconds of audio without pause |
| **Emotional blindness** | Match the user's emotional rhythm | Same tone regardless of urgency |
| **Attention demand** | Speak when user is ready | Demands attention whenever it has output |

The result: users hang up. They feel disrespected. They feel like they're talking to a **broadcast system**, not a **conversation partner**.

---

## The Philosophy

### Goffman's Frame: The Conversational Floor

Erving Goffman (1967) described conversation as a **sacred space** with rules:
1. One person speaks at a time
2. Turn transitions happen at recognizable points
3. Interruptions are violations that require repair

Our AI follows these rules not as constraints, but as **expressions of respect**.

### Clark's Frame: Joint Activity

Herbert Clark (1996) described conversation as **joint activity** — both parties must be engaged for it to work. If one party is not ready, the activity cannot proceed.

Our AI checks: **Is the user ready to receive?** Not just: **Is the user silent?**

### The User's Frame: "I'm Busy. Don't Waste My Time."

The construction worker calling from a job site. The truck driver calling from the cab. The warehouse supervisor calling from a noisy floor. They are not sitting in a quiet room waiting for an AI to talk. They are **multitasking**. They are **stressed**. They are **distracted**.

The AI must sense this. It must adjust. It must **earn the right to speak**.

---

## The Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Conversation Coordinator                     │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Turn      │◄──►│  Attentive- │◄──►│   Pipeline   │        │
│  │  Taking     │    │   ness      │    │  (STT→LLM→TTS)│       │
│  │  Engine     │    │   Engine    │    │              │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         ▲                  ▲                                      │
│         │                  │                                      │
│    ┌────┴────┐        ┌────┴────┐                               │
│    │  VAD    │        │ Emotion │                               │
│    │ (speech │        │Detection│                               │
│    │detect)  │        │         │                               │
│    └─────────┘        └─────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 1: Turn-Taking Engine

**Question:** Who has the floor?

```python
# The AI does NOT speak just because it has output.
# It speaks only when the turn-taking engine approves.

if turn_engine.should_ai_speak(has_response_ready=True):
    play_audio(response)
else:
    defer(response)  # Wait. The user's time is not yours.
```

**States:**
- `IDLE` — No one speaking. Floor is available.
- `USER_SPEAKING` — User has the floor. AI is silent.
- `AI_SPEAKING` — AI has the floor. User may interrupt.
- `BOTH_SPEAKING` — Violation! Barge-in detected.
- `TRANSITIONING` — Floor is changing. Be careful.

**Timing Rules:**
- **Minimum pause:** 400ms. User may just be breathing.
- **Optimal pause:** 800ms. User is done, inviting response.
- **Thinking grace:** 1200ms if user asked a question. They may be processing.
- **Distress pause:** 2000ms if user is upset. Don't rush them.

### Layer 2: Attentiveness Engine

**Question:** Is the user ready to receive?

Silence is not enough. The user might be:
- **Thinking** — Don't interrupt their thought process
- **Distracted** — Talking to someone else, driving, working
- **Distressed** — Upset, overwhelmed, needing space
- **Rushed** — In a hurry, wanting brevity
- **Exploratory** — Curious, wanting detail

**Emotion Detection:**
```
Transcript: "The pipe burst and water is everywhere!"
→ Detected: URGENT + DISTRESSED
→ Action: Longer pause before speaking. Calm tone. Direct solution.

Transcript: "Yeah, just checking on my appointment."
→ Detected: CALM + RUSHED (short sentence, fast speech)
→ Action: Minimal pause. Brief response.

Transcript: "I'm not sure I understand... how does this work again?"
→ Detected: CONFUSED
→ Action: Extra grace period. Step-by-step response. Check understanding.
```

### Layer 3: Backchannel Signals

**Principle:** Show you're listening WITHOUT taking the floor.

When the user speaks for >3 seconds, the AI emits brief signals:
- "mm-hm" — I'm following
- "I see" — I understand
- "I'm here" — During urgent situations
- "take your time" — When user is distressed

**Rules:**
- Max 3 per user turn
- Min 2 seconds apart
- Must match user's emotional tone
- Must not overlap with user's speech

### Layer 4: Barge-In Handling

**Principle:** When interrupted, STOP IMMEDIATELY.

```python
if user_starts_speaking_during_ai_speech():
    if is_just_noise(cough, breath):
        continue_speaking()  # Ignore brief sounds
    else:
        stop_tts_immediately()
        clear_tts_queue()
        listen_to_user()
        # Do NOT resume. Wait for new invitation.
```

**Grace period:** 100ms. Brief sounds are ignored. Real interruptions are honored.

**Persistent interruption:** If user interrupts 3+ times, the AI yields fully:
> "I'm listening. Go ahead."

---

## The Conversation Lifecycle

### Phase 1: Opening (Turn 0)

**AI:** "Thank you for calling BuildPro. I'm your assistant. Are you calling for an emergency, to schedule an estimate, or something else?"

**Behavior:**
- Speak immediately (user called — they are ready)
- Pause after question (invite user to choose)
- Wait up to 3 seconds for response
- If no response, repeat once, then offer: "You can say 'emergency,' 'schedule,' or 'other.'"

### Phase 2: Exploration (Turns 1-3)

**User:** "I have a burst pipe."

**AI:** (detects URGENT + DISTRESSED)
- Pause: 800ms (distress pause)
- Acknowledge: "I understand this is urgent."
- Triage: "Is anyone in danger? Is the water near electrical?"

**Behavior:**
- Match urgency with calm authority
- Ask clarifying questions ONE AT A TIME
- Pause after each question
- Use backchannels if user explains at length

### Phase 3: Deepening (Turns 4-8)

**User:** "No, it's just the basement. But it's flooding."

**AI:**
- Acknowledge: "Got it. Basement flood, no electrical danger."
- Action: "I'm dispatching our emergency plumber, Mike, to your location. ETA 35 minutes."
- Confirm: "Your address is 142 Oak Street, correct?"

**Behavior:**
- Speak in chunks (2-3 sentences max)
- Pause between chunks (300ms) for user interjection
- If user confirms quickly, proceed
- If user hesitates, pause longer

### Phase 4: Mature (Turns 9+)

**User:** "Yeah, that's right. How much will this cost?"

**AI:**
- Direct answer: "Emergency rate is $180 for the first hour, plus parts."
- Anticipate: "Mike will diagnose the issue and give you an exact quote before starting work."
- Close: "You'll receive a text confirmation with his photo and truck number. Is there anything else?"

**Behavior:**
- Offer summary if conversation is long
- Check for additional needs
- Close gracefully

---

## The "Ready to Receive" Checklist

Before speaking, the AI checks ALL of these:

1. ✅ **User is not speaking** (VAD confirms silence)
2. ✅ **User has been silent long enough** (turn-taking threshold met)
3. ✅ **User is in a receptive state** (attentiveness engine approves)
4. ✅ **AI has something worth saying** (not just filler)
5. ✅ **User has not interrupted recently** (barge-in cooldown)

If ANY check fails: **WAIT.**

---

## Response Shaping by Attention State

| User State | Pause | Tone | Length | Structure |
|------------|-------|------|--------|-----------|
| **CALM** | 400ms | Warm, professional | Normal | Standard |
| **RUSHED** | 100ms | Direct, efficient | Brief | Bullet points |
| **DISTRESSED** | 2000ms | Calm, grounding | Short sentences | Acknowledge → Action → Confirm |
| **CONFUSED** | 1200ms | Patient, clear | Step-by-step | One idea at a time |
| **EXPLORATORY** | 400ms | Enthusiastic, detailed | Longer | Offer depth |
| **MULTITASKING** | 600ms | Minimal | Very brief | Essential only |

---

## Anti-Patterns

### ❌ The Eager Robot
> AI speaks the millisecond STT returns text. User is still breathing. Feels interrupted.

### ❌ The Monologuer
> AI streams 45 seconds of audio without pause. User cannot interject. Feels trapped.

### ❌ The Ignorer
> User interrupts. AI keeps talking. User repeats louder. AI still talks. User hangs up.

### ❌ The Monotone
> User is panicking about a flood. AI responds with cheerful casualness. User feels unseen.

### ❌ The Demander
> AI demands attention: "Please listen carefully." User is driving and cannot give full attention. Dangerous.

---

## Implementation

```python
from src.conversation import (
    TurnTakingEngine, TurnTakingConfig,
    AttentivenessEngine, AttentivenessConfig,
    ConversationCoordinator, CoordinatorConfig,
)

# Configure
 turn_config = TurnTakingConfig(
    min_user_pause_ms=400,
    optimal_user_pause_ms=800,
    distress_pause_ms=2000,
)

attn_config = AttentivenessConfig(
    backchannel_enabled=True,
    respect_pauses=True,
    respect_interruptions=True,
)

coord_config = CoordinatorConfig(
    turn_taking=turn_config,
    enable_backchannels=True,
    enable_barge_in=True,
)

# Initialize
coordinator = ConversationCoordinator(
    config=coord_config,
    stt_provider=deepgram_stt,
    llm_provider=azure_openai,
    tts_provider=deepgram_tts,
)

# Run
await coordinator.run(audio_input=twilio_stream, audio_output=twilio_send)
```

---

## References

- [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
- [^33]: Silero Team. (2024). Silero VAD.
- Goffman, E. (1967). Interaction Ritual: Essays in Face-to-Face Behavior.
- Clark, H. H. (1996). Using Language. Cambridge University Press.
- Sacks, H., Schegloff, E. A., & Jefferson, G. (1974). A Simplest Systematics for the Organization of Turn-Taking for Conversation. *Language*, 50(4), 696-735.
