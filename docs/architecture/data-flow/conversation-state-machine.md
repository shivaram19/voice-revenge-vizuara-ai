# Data Flow: Conversation State Machine

**Version**: 1.0  
**Date**: 2026-04-25

---

## States

```
                    ┌─────────────┐
         ┌─────────►│    IDLE     │◄────────┐
         │          │             │         │
         │          └──────┬──────┘         │
         │                 │                │
         │     (vad_start) │                │
         │                 ▼                │
         │          ┌─────────────┐         │
         │          │  LISTENING  │         │
         │          │             │         │
         │          └──────┬──────┘         │
         │                 │                │
         │   (stt_final)   │                │
         │                 ▼                │
         │          ┌─────────────┐         │
         │          │  THINKING   │         │
         │          │   (LLM)     │         │
         │          └──────┬──────┘         │
         │                 │                │
         │  (tts_started)  │                │
         │                 ▼                │
         │          ┌─────────────┐         │
         └──────────┤  SPEAKING   │         │
   (vad_start /    │             │─────────┘
    tts_done)      └─────────────┘   (tts_done)
```

---

## State Definitions

### IDLE
**Entry**: Session initialized or previous turn complete.
**Activity**: Waiting for VAD to detect speech.
**Timeout**: 5 minutes → session ends.

### LISTENING
**Entry**: VAD reports `speech_start`.
**Activity**: 
- Stream audio to STT service.
- Display partial transcripts to user (if UI present).
- Fast Talker begins speculative LLM generation on partial transcript [^16].

**Transitions**:
- `stt_final` + `speech_final` → THINKING
- `vad_start` during SPEAKING → INTERRUPTED (not shown for clarity)

### THINKING
**Entry**: STT returns final transcript.
**Activity**:
1. Query Memory Service (Fast Talker cache first).
2. Build LLM prompt with context + retrieved memory.
3. Begin LLM streaming generation.
4. If tool call detected → pause generation → execute tool → resume.

**Transitions**:
- First sentence complete → SPEAKING (TTS starts)
- Tool call required → TOOL_EXECUTION → back to THINKING

### SPEAKING
**Entry**: TTS receives first sentence.
**Activity**:
- Stream audio chunks to client via SFU.
- Continue receiving LLM tokens; buffer next sentence.
- Monitor VAD for barge-in.

**Transitions**:
- `vad_start` (barge-in) → LISTENING (abort TTS, flush LLM)
- `tts_complete` + no more LLM tokens → IDLE

---

## Event Schema

```protobuf
message ConversationEvent {
  string session_id = 1;
  int64 timestamp_ms = 2;
  EventType type = 3;
  bytes payload = 4;
}

enum EventType {
  VAD_SPEECH_START = 0;
  VAD_SPEECH_END = 1;
  STT_PARTIAL = 2;
  STT_FINAL = 3;
  LLM_TOKEN = 4;
  LLM_TOOL_CALL = 5;
  TTS_AUDIO_CHUNK = 6;
  TTS_SENTENCE_START = 7;
  TTS_SENTENCE_END = 8;
  TOOL_RESULT = 9;
  BARGE_IN = 10;
  SESSION_END = 11;
}
```

---

## Timing Constraints

| Transition | Max Latency | Measurement |
|------------|-------------|-------------|
| VAD_START → STT_PARTIAL | <100ms | First partial transcript |
| VAD_END → STT_FINAL | <300ms | Final transcript confidence |
| STT_FINAL → LLM_TTFT | <200ms | First token generated |
| LLM_TTFT → TTS_TTFB | <150ms | First audio byte |
| BARGE_IN → TTS_ABORT | <50ms | Audio playback stops |

---

## Failure Handling

| Failure | State Behavior |
|---------|---------------|
| STT timeout (>500ms) | Degrade to cloud API; log incident |
| LLM timeout (>1s) | Return "Let me think..." audio; retry |
| TTS timeout (>300ms) | Skip audio, send text transcript |
| Memory cache miss | Fall back to LLM context only; background fetch |
| Network partition | Buffer events; replay on reconnect |

---

## References
[^16]: SigArch. (2026). Section 4.2. Streaming pipeline architecture with speculative LLM generation on interim transcripts. *arXiv:2603.05413*.
[^16]: SigArch. (2026). Section 4.2. Streaming pipeline architecture with speculative LLM generation on interim transcripts. *arXiv:2603.05413*.

[^9]: SigArch. (2026). Section 4.2. Streaming pipeline architecture with speculative LLM generation on interim transcripts. *arXiv:2603.05413*.
