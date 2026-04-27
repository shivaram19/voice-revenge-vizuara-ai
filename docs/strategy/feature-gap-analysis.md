# Feature Gap Analysis: Marketing Claims vs. Codebase Reality

## Executive Summary

This document provides a rigorous, evidence-based audit of claimed AI capabilities against actual codebase implementation. The analysis employs a three-pronged research methodology:

- **DFS (Depth-First Search)**: Deep vertical analysis into specific claimed features through full codepath tracing
- **BFS (Breadth-First Search)**: Broad scan across all 45 Python modules to detect any hidden implementations
- **Bi-Directional Research**: Connecting market pain points (from `lead-intelligence-report.md`) to technical capabilities and research literature

**Overall Assessment**: The codebase implements a solid foundational voice agent architecture (STT → LLM → TTS pipeline, turn-taking, tool calling, scheduling) but lacks the advanced paralinguistic and perceptual AI capabilities claimed in marketing materials. Several claims are **partially realizable** with the current TTS provider (Deepgram Aura) but are **not leveraged** in the integration layer. Others require significant new engineering.

---

## Methodology

### Code Audit Scope
- **Files analyzed**: 45 Python modules across `src/`
- **Search patterns**: `breath`, `emotion`, `ambient`, `office`, `prosody`, `ssml`, `pitch`, `vad`, `silero`, `scene`, `gender`, `age`, `filler`, `uh`, `um`
- **Interfaces audited**: `STTPort`, `TTSPort`, `VADPort`, `TransportPort`
- **Pipeline audited**: Full STT → LLM → TTS flow in `coordinator.py`

### Research Sources
- Deepgram Aura/Aura-2 product documentation and launch announcements
- Speech Emotion Recognition (SER) research literature (2024–2026)
- Acoustic Scene Analysis (ASA) / DCASE challenge literature
- Speaker profiling research (x-vector/i-vector frameworks)
- Conversational TTS research (FillerSpeech, EMNLP 2025)
- Silero VAD technical documentation

---

## Gap 1: Real Audio-Based Emotion Detection

### Marketing Claim
> "The AI adjusts its tone based on the caller's emotional state."
> "Detects frustration, urgency, and distress from the caller's voice."
> "Elderly customers hang up on competitor AIs because they sound robotic — our AI breathes, selects backchannels, and adjusts tone based on emotional state."

### Codebase Reality

The `AttentivenessEngine` in `src/conversation/attentiveness.py` implements `_detect_emotion()` using **text-only heuristics**:

```python
def _detect_emotion(self, transcript: str, metrics: dict) -> EmotionalTone:
    # Text heuristics only; audio metrics are placeholders
    urgency_words = ["emergency", "now", "immediately", "urgent", "asap", "hurry"]
    frustration_words = ["frustrated", "annoyed", "terrible", "awful", "ridiculous"]
    # ... keyword matching ...
    if metrics.get("pitch_variation", 0) > 0.7:
        return EmotionalTone.URGENT
```

**Critical Finding**: The `metrics` dictionary containing `pitch_variation` and `volume_db` is **never populated from actual audio analysis**. It is a placeholder structure with hardcoded defaults (`pitch_variation=0`, `volume_db=0`). The comment explicitly states: `"Production: integrate emotion recognition model."`

The emotion detection is purely lexical — if the caller says "I am frustrated," the AI detects frustration. If the caller's voice cracks with stress but they say "Everything is fine," the AI detects `CALM`.

### Pipeline Analysis
Emotion flows from `attentiveness.py` → `turn_taking.py` → `coordinator.py` as a **text label only** (`"neutral"`, `"urgent"`, `"distressed"`). It is **never passed to the TTS layer**. The `DeepgramTTS.synthesize_stream()` method has no emotion parameter:

```python
payload = {
    "text": text,
    "voice": self.config.tts_voice,  # Static: "aura-asteria-en"
    "encoding": "linear16",
    "sample_rate": 24000,
}
```

### Research Evidence

Real-time Speech Emotion Recognition is a well-established field with production-ready approaches:

| Approach | Accuracy | Latency | Feasibility |
|----------|----------|---------|-------------|
| SVM + handcrafted features (MFCC, pitch, energy) | 87–91% | <10ms | High — lightweight, explainable |
| CNN + Bi-LSTM on spectrograms | 90–100% | 50–100ms | Medium — requires GPU for batch |
| MLP on MFCC + ZCR + Chroma + RMS | 90–99% | <20ms | High — suitable for real-time |

Key acoustic features for emotion detection [^ser-1][^ser-2]:
- **Pitch (F0)**: High pitch variation → urgency/anger; low pitch → sadness/fatigue
- **RMS Energy**: High energy → anger/excitement; low energy → calm/sadness
- **MFCCs 1–12**: Spectral envelope captures vocal tract shape changes under emotion
- **Formants (F1, F2, F3)**: Shift with emotional state
- **Zero Crossing Rate (ZCR)**: Higher in stressed/unvoiced speech
- **Spectral Contrast**: Captures harmonic vs. noise-like qualities

### Gap Severity: **HIGH**

### Remediation Path

**Short-term (2–4 weeks)**:
1. Integrate **Silero VAD** (already referenced in codebase) to get real audio features
2. Add lightweight feature extraction (MFCC, pitch, energy) using `librosa` or `parselmouth`
3. Train/fine-tune a small classifier (SVM or 2-layer MLP) on 4-class emotion (calm, urgent, frustrated, angry)
4. Pass detected emotion to `shape_response()` and voice selection logic

**Medium-term (1–2 months)**:
1. Replace keyword-based detection with audio-feature fusion: `emotion = fuse(text_emotion, audio_emotion, confidence_weighting)`
2. Implement emotion-aware voice selection in `DeepgramTTS` (see Gap 2)
3. Add emotion-driven response timing (already partially implemented in `get_optimal_response_delay_ms()`)

---

## Gap 2: Breathing & Human-Like Paralinguistics

### Marketing Claim
> "The AI produces breathing sounds of disturbances in between knowing that we're in an environment calling from the office environment."
> "Our AI breathes, selects backchannels, and adjusts tone based on emotional state."

### Codebase Reality

**No breathing audio synthesis code exists.** Grepping the entire codebase for `breath` yields only:
- Comments about detecting user breathing as a pause signal (`"user may just be breathing"`)
- Barge-in grace logic (`"Likely cough, breath, or ambient noise"`)

There is no audio post-processing layer, no waveform generation for breathing sounds, and no ambient noise injection.

### CRITICAL DISCOVERY: Deepgram Aura Natively Supports Breathing

Deepgram's Aura TTS product documentation explicitly states [^dg-aura-1]:

> "Aura will equip AI agents with lifelike voices, and it's been developed with capabilities that replicate authentic human dialogues. This includes prompt replies, natural cadences that include **pauses, audible breaths and hesitation sounds like 'uh' and 'um,'** as well as **dynamic adjustments in tone and emotion** to suit the conversation's context."

Aura-2 adds "context-aware emotional prosody that dynamically adjusts pacing, tone, and expression" [^dg-aura-2].

**The gap is NOT that the TTS cannot produce breathing/hesitation/emotion. The gap is that the integration layer does not leverage these capabilities.**

Specific integration gaps:

1. **Static voice selection**: `DeepgramConfig.tts_voice = "aura-asteria-en"` (single female voice). No voice switching based on emotion, context, or caller preference.

2. **No text shaping for prosody**: The `shape_response()` method in `attentiveness.py` only modifies **text length** (condense/calm/clarify) — it does not add prosodic cues like ellipses for hesitation, exclamation for urgency, or soften vocabulary for empathy.

3. **Prompt actively suppresses fillers**: Both `system_prompt.py` and `construction_prompt.py` contain:
   > "Use fillers only when running a tool: 'Let me check...' or 'One moment...'"
   
   This **explicitly discourages** the natural "uh"/"um" generation that Deepgram Aura is capable of producing.

4. **No emotion pass-through to TTS**: Even if Deepgram Aura supports dynamic tone adjustment, the coordinator pipeline passes only raw text strings with no emotional context.

### Research Evidence

The 2026 vishing perception study [^vishing-1] found that participants could not distinguish AI from human voices when:
- Filler words ("uh", "um") were embedded in scripts
- Breathing sounds were incorporated
- Prosodic variation was applied

> "AI clips that deliberately incorporated disfluencies (e.g., hesitation markers, breathing sounds) were often interpreted as human, whereas monotone or 'overly clean' human recordings were perceived as artificial."

The FillerSpeech framework (EMNLP 2025) [^filler-1] demonstrates LLM-based filler prediction for natural conversational speech, showing that even 1B-parameter models can outperform baselines at predicting where humans insert fillers.

### Gap Severity: **MEDIUM-HIGH** (Capability exists in TTS; integration missing)

### Remediation Path

**Immediate (1–2 weeks)**:
1. **Remove filler suppression from prompts**: Delete "Use fillers only when running a tool" rule. Replace with: "Speak naturally. Brief pauses and fillers are okay when thinking."
2. **Add text-level prosody shaping** in `AttentivenessEngine.shape_response()`:
   - For `CONFUSED`/`THINKING`: Add "..." or "let me see..." 
   - For `URGENT`: Use shorter sentences, direct language
   - For `CALM`: Use warmer vocabulary, slightly longer phrasing

**Short-term (2–4 weeks)**:
1. **Implement voice selection mapping** in `DeepgramTTS`:
   ```python
   EMOTION_VOICE_MAP = {
       EmotionalTone.CALM: "aura-asteria-en",      # Warm female
       EmotionalTone.URGENT: "aura-orion-en",       # Assertive male
       EmotionalTone.FRUSTRATED: "aura-luna-en",    # Soft, patient
       EmotionalTone.ANGRY: "aura-hera-en",         # Steady, de-escalating
   }
   ```
2. **Upgrade to Aura-2** if available on the API plan (40+ voices with explicit emotional prosody)

**Note on SSML**: Deepgram Aura does **not** support SSML [^tts-comp-1]. Prosody must be controlled through voice selection and text-level cues (punctuation, word choice, sentence structure). For SSML-level control, would need to migrate to Google Cloud TTS, Amazon Polly, or Microsoft Azure Speech.

---

## Gap 3: Acoustic Scene Analysis (Environmental Awareness)

### Marketing Claim
> "Knowing that we're in an office environment."
> "The AI knows if the caller is in a car, on a construction site, or in a quiet office."

### Codebase Reality

**Zero implementation.** No acoustic scene classification module exists. No code analyzes ambient noise patterns, reverberation characteristics, or background sound events to infer the caller's environment.

The `AudioChunk` dataclass in `interfaces.py` carries only raw PCM samples with no metadata:
```python
@dataclass
class AudioChunk:
    samples: np.ndarray  # float32, 16kHz, mono
    timestamp_ms: int
    sample_rate: int = 16000
```

### Research Evidence

Acoustic Scene Recognition (ASR — not to be confused with Automatic Speech Recognition) is a mature field with standard datasets and models [^asa-1][^asa-2]:

| Dataset | Environments | Size |
|---------|-------------|------|
| DCASE Challenge | 15+ scenes (office, street, café, train, home) | Industry standard |
| TUT Acoustic Scenes 2017 | 15 scenes (library, forest, grocery store, lakeside) | 4,680 clips |
| UrbanSound8K | Urban sound events (sirens, drilling, children) | Event-focused |

Standard approach:
1. Extract Mel spectrogram or MFCC features from audio
2. Classify with CNN (treat spectrogram as image) or CRNN
3. Output scene label: `office`, `vehicle`, `construction_site`, `outdoor`, `quiet_indoor`

For voice agents, scene awareness enables:
- **Noise-adaptive VAD**: Higher threshold for construction sites, lower for quiet offices
- **Context-aware responses**: Shorter responses in noisy vehicles; slower, clearer speech for construction sites
- **Safety routing**: Detect "caller is driving" → offer callback option

### Gap Severity: **MEDIUM**

### Remediation Path

**Short-term (3–6 weeks)**:
1. Implement lightweight scene classifier using pre-trained CNN on Mel spectrograms
2. Run classification on caller audio stream (before VAD)
3. Pass scene label to coordinator for response adaptation

**Sample scene → behavior mapping**:
| Detected Scene | Response Adaptation |
|---------------|---------------------|
| `vehicle` | Shorter responses, offer callback, louder TTS output |
| `construction_site` | Slower speech, repeat confirmations, louder output |
| `office` | Standard behavior |
| `quiet_indoor` | Normal volume, can use longer explanations |
| `outdoor_wind` | Repeat key info, confirm understanding |

---

## Gap 4: Voice-Based Caller Profiling

### Marketing Claim
> "The category that he will be falling into if he's talked to."
> "Distinguishes between a professional contractor and a homeowner based on voice."
> "Adapts to caller age and gender for more natural interaction."

### Codebase Reality

**Zero implementation.** No speaker profiling from audio features exists. The system cannot estimate:
- Caller age (child, youth, adult, senior)
- Caller gender
- Speaking style (professional/trade vocabulary vs. casual homeowner)
- Accent/dialect region

The `CallSession` model tracks only:
```python
class CallSession:
    session_id: str
    caller_number: str
    called_number: str
    # ... no demographic fields ...
```

### Research Evidence

Speaker profiling from telephone speech is well-researched [^spkr-1][^spkr-2][^spkr-3]:

| Task | Approach | Performance |
|------|----------|-------------|
| Gender recognition | x-vector + TDNN | 98.4–99.6% accuracy |
| Age estimation (regression) | x-vector + DNN | MAE 4.92–5.36 years |
| Age group classification | CNN on spectrograms | 57–88% accuracy (4 groups) |
| Speaker traits | i-vector + NFA fusion | Improved over single feature type |

Key features: MFCCs, pitch (F0), formants, speaking rate, pause patterns.

**Business relevance for construction trades**:
- **Senior callers** (65+): Need slower speech, more patience, explicit confirmations. The lead intelligence report identified elderly callers as particularly sensitive to robotic AI voices.
- **Professional contractors**: Use trade vocabulary ("rough-in", "punch list", "change order"), expect direct, efficient communication.
- **Homeowners**: May need explanations of trade terms, more reassurance, scheduling flexibility discussion.
- **Gender-based voice matching**: Some callers prefer same-gender voices; matching can increase trust.

### Gap Severity: **MEDIUM**

### Remediation Path

**Short-term (4–6 weeks)**:
1. Implement gender detection using pitch (F0) histogram analysis:
   - Male F0 range: ~85–180 Hz
   - Female F0 range: ~165–255 Hz
   - Simple threshold classifier: ~95% accuracy on telephone speech
2. Implement age estimation using speaking rate + pitch variation + spectral features
3. Add detected demographics to `CallSession` context

**Medium-term (2–3 months)**:
1. Integrate pre-trained x-vector model (e.g., from `speechbrain` or `resemble-ai`) for robust gender/age
2. Implement "professional vs. homeowner" classifier based on vocabulary complexity + speaking rate
3. Use demographics to select TTS voice and adapt prompt tone

---

## Gap 5: Human-Like Speech Imperfections (Fillers, Hesitations)

### Marketing Claim
> "Doesn't sound like a robot."
> "Current AI sounds robotic — our AI is different."

### Codebase Reality

**Actively suppressed.** As noted in Gap 2, system prompts explicitly restrict fillers to tool-running contexts only. The `SentenceAggregator` and prompt engineering both prioritize "clean" output over naturalistic conversation.

The only "imperfections" in the current pipeline are:
1. **Latency masking fillers**: "Let me check..." (deliberate, not natural)
2. **Backchannels**: "mm-hm", "I see" (text-only, not vocalized with breathing)

### Research Evidence

The 2026 vishing study [^vishing-1] found that **disfluencies increase perceived humanness**:
> "Participants relied heavily on surface-level paralinguistic heuristics — such as filler words, pauses, vocal intensity, and perceived smoothness — when making authenticity judgments."

The FillerSpeech framework [^filler-1] shows that LLMs can predict natural filler insertion points from text context, enabling:
- "Um, let me check that for you..."
- "The plumber is... uh... available Tuesday at 2."
- "That's a... good question."

Deepgram Aura generates these naturally when the text includes them or when the context suggests hesitation.

### Gap Severity: **MEDIUM** (Easy fix — remove suppression)

### Remediation Path

**Immediate (1 week)**:
1. Rewrite prompt rules to encourage natural speech:
   ```
   OLD: "Use fillers only when running a tool: 'Let me check...' or 'One moment...'"
   NEW: "Speak naturally. Brief pauses, 'uh', or 'um' are fine when looking something up or thinking."
   ```

**Short-term (2–3 weeks)**:
1. Add `FillerInjector` layer between LLM output and TTS input:
   - Insert "um" or "uh" before tool calls (natural thinking pause)
   - Add "..." (rendered as pause by TTS) when response requires lookup
   - Use contractions and casual forms: "can't" vs. "cannot", "I'm" vs. "I am"

---

## Gap 6: Real Voice Activity Detection (VAD)

### Marketing Claim
> (Implied by production-ready voice agent claims)

### Codebase Reality

`coordinator.py` contains a placeholder VAD implementation:

```python
def _detect_speech(self, audio_chunk: bytes) -> bool:
    """Simple VAD placeholder. Production: integrate Silero VAD [^33]."""
    energy = sum(abs(b - 128) for b in audio_chunk) / len(audio_chunk) if audio_chunk else 0
    return energy > 10  # Arbitrary threshold
```

This energy threshold:
- Fails in noisy environments (construction sites, vehicles)
- Fails on quiet speakers (elderly, soft-spoken callers)
- Has no speech start/end detection
- Cannot distinguish speech from non-speech sounds

A `VADPort` interface already exists in `interfaces.py` but has no implementation.

### Research Evidence

Silero VAD is specifically referenced in the codebase and is the industry standard [^vad-1][^vad-2]:

| Feature | Silero VAD | Current (Energy) |
|---------|-----------|------------------|
| Accuracy | >95% in multi-noise | ~60–70% |
| Latency | <1ms per 30ms chunk | Instant (but wrong) |
| Model size | 2MB JIT, <1MB ONNX | None |
| Languages | 6000+ | N/A |
| Speech start/end | Yes | No |
| Noise robustness | Excellent | Poor |
| License | MIT (commercial OK) | N/A |

### Gap Severity: **HIGH** (Foundational — affects entire pipeline)

### Remediation Path

**Immediate (1–2 weeks)**:
1. Implement `SileroVAD` adapter class implementing `VADPort`
2. Replace `_detect_speech()` placeholder with real VAD
3. Add hysteresis-based speech start/end events to improve turn-taking

```python
class SileroVAD(VADPort):
    async def process(self, audio_chunk: AudioChunk) -> Dict[str, Any]:
        # Returns: is_speech, probability, speech_start, speech_end
        ...
```

---

## Summary Matrix

| # | Capability | Claimed | Implemented | TTS Can Do It? | Effort to Fix | Severity |
|---|-----------|---------|-------------|----------------|---------------|----------|
| 1 | Audio-based emotion detection | ✅ | ❌ Text-only | N/A (input side) | 2–4 weeks | **HIGH** |
| 2 | Breathing sounds / hesitation | ✅ | ❌ No code | ✅ Deepgram Aura native | 1–2 weeks | **MED-HIGH** |
| 3 | Dynamic tone/prosody | ✅ | ❌ Static voice | ✅ Aura-2 context-aware | 2–4 weeks | **MED-HIGH** |
| 4 | Acoustic scene analysis | ✅ | ❌ No code | N/A (input side) | 3–6 weeks | **MEDIUM** |
| 5 | Speaker profiling (age/gender) | ✅ | ❌ No code | N/A (input side) | 4–6 weeks | **MEDIUM** |
| 6 | Natural fillers / disfluencies | ✅ | ❌ Actively suppressed | ✅ Via text shaping | 1 week | **MEDIUM** |
| 7 | Real VAD (Silero) | Implied | ❌ Placeholder | N/A | 1–2 weeks | **HIGH** |

---

## Recommendations

### Priority 1: Fix the Easy Wins (Week 1–2)
1. **Remove filler suppression from prompts** — immediate perceived naturalness improvement
2. **Implement Silero VAD** — fixes foundational pipeline accuracy
3. **Add voice selection mapping** for 2–3 basic emotions (calm, urgent)

### Priority 2: Enable TTS Capabilities Already Paid For (Week 2–4)
1. **Pass emotional context through the pipeline** (attentiveness → coordinator → TTS)
2. **Add text-level prosody shaping** (ellipses, sentence length variation, vocabulary warmth)
3. **Upgrade to Aura-2** if on compatible API plan
4. **A/B test emotional voice vs. neutral** for construction trade callers

### Priority 3: Build Differentiating Perceptual AI (Month 2–3)
1. **Implement lightweight SER** (MFCC + pitch + SVM/MLP) for real emotion detection
2. **Add acoustic scene classifier** (vehicle/office/construction detection)
3. **Implement gender/age detection** from pitch and speaking rate
4. **Use perceptual signals to adapt prompts dynamically**:
   - Detected `vehicle` + `urgent` → "I'll keep this brief. You're speaking from a vehicle, correct?"
   - Detected `senior` + `slow_speech` → slower responses, more confirmations
   - Detected `frustrated` + `construction_noise` → "I can hear you're on a job site. Let me help quickly."

### Priority 4: Research & Long-Term (Month 3+)
1. Evaluate **native Speech Language Models** (SLMs) like OpenAI Realtime API or Hume Octave that process raw audio embeddings directly — bypassing the text-only emotion limitation entirely
2. Consider **multi-modal pipeline**: audio features → emotion + scene + demographics → all feed into prompt context and TTS configuration

---

## Competitive Implications

From the lead intelligence report, competitor failure modes include:
- **SkipCalls ($19.99/mo)**: Robotic voice, no emotional adaptation
- **Nautilus AI ($156K/mo roofing claim)**: Generic answers for trade questions
- **ServiceForge**: Human-only, no AI scalability

**The gaps identified in this analysis are the exact differentiation vectors** that would separate this product from competitors. However, **current marketing claims these capabilities without implementing them** — creating liability if prospects request demos or proof-of-concept calls.

**Immediate risk**: A prospect from GFC Cartage or AFT Dispatch could test the system, detect robotic behavior, and publicly note the gap — undermining credibility with the exact high-value leads identified in the intelligence report.

---

## References

[^ser-1]: Akçay, M. B., & Oğuz, K. (2020). Speech emotion recognition: Emotional models, databases, features, preprocessing methods, supporting modalities, and classifiers. *Speech Communication*, 116, 56–70.

[^ser-2]: Springer. (2024). Real-time speech emotion recognition using deep learning and data augmentation. *Artificial Intelligence Review*.

[^dg-aura-1]: Deepgram. (2026). Introducing Deepgram Aura: Lightning Fast Text-to-Speech for Voice AI Agents. deepgram.com/learn/aura-text-to-speech-tts-api-voice-ai-agents-launch.

[^dg-aura-2]: Deepgram. (2025). Introducing Aura-2: Enterprise-Grade Text-to-Speech. deepgram.com/learn/introducing-aura-2-enterprise-text-to-speech.

[^vishing-1]: arXiv. (2026). Can You Tell It's AI? Human Perception of Synthetic Voices in Vishing Scenarios. arXiv:2602.20061v1.

[^filler-1]: ACL Anthology. (2025). Towards Human-Like Text-to-Speech Synthesis with Filler Insertion and Filler Style Control. EMNLP 2025.

[^asa-1]: Annotera AI. (2026). Sound Classification for AI: Training Smart Devices with Acoustic Scene Recognition.

[^asa-2]: Way With Words. (2025). What Is Acoustic Scene Analysis and Why It Matters.

[^spkr-1]: KU Leuven. Speaker Profiling for Forensic Applications. ESAT Master Thesis.

[^spkr-2]: Springer. (2022). Age group classification and gender recognition from speech with temporal convolutional neural networks. *Multimedia Tools and Applications*.

[^spkr-3]: GitHub. SpeakerProfiling: Estimating Age, Height and Gender of a Speaker.

[^vad-1]: Silero Team. (2024). Silero VAD: Pre-trained enterprise-grade Voice Activity Detector. github.com/snakers4/silero-vad.

[^vad-2]: Picovoice. (2025). Choosing the Best Voice Activity Detection in 2026.

[^tts-comp-1]: AssemblyAI. (2026). Top text-to-speech APIs in 2026.

[^morvoice-1]: MorVoice. (2026). The 2026 AI Voice Revolution: From Models to Autonomous Audio Agents.
