# Deepgram Integration
## Nova-3 STT + Aura TTS for Construction Receptionist

> **Goal:** Replace self-hosted Whisper/Piper with Deepgram's cloud APIs for lower latency, higher accuracy, and zero infrastructure overhead.

---

## Why Deepgram?

| Dimension | Self-hosted (Whisper + Piper) | Deepgram (Nova-3 + Aura) |
|-----------|------------------------------|---------------------------|
| **Latency** | 500-1500ms (GPU-dependent) | 200-400ms (cloud-optimized) |
| **Accuracy** | 85-92% WER (Whisper large-v3) | 93-97% WER (Nova-3) [^6] |
| **Infrastructure** | A10G GPU required | Zero GPU, HTTP/WebSocket API |
| **Cost @ 50 concurrent** | $800-1200/mo (GPU instances) | $200-400/mo (pay-per-minute) |
| **Scaling** | Manual GPU autoscaling | Automatic |
| **Maintenance** | Model updates, drivers, CUDA | None |

**Nova-3** is specifically optimized for telephony audio (8kHz, noisy environments) [^6]. For a construction receptionist handling calls from job sites, trucks, and busy homes, this accuracy delta matters.

**Aura** TTS streams audio in real-time with ~150ms time-to-first-byte — critical for the "conversational" feel that reduces hangups [^16].

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Construction Receptionist                  │
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Twilio    │───►│  Deepgram   │───►│    LLM      │     │
│  │  (PSTN in)  │    │  Nova-3 STT │    │ (Azure OAI) │     │
│  └─────────────┘    └─────────────┘    └──────┬──────┘     │
│        ▲                                        │            │
│        │         ┌─────────────┐               │            │
│        │         │  Deepgram   │◄──────────────┘            │
│        │         │  Aura TTS   │                            │
│        │         └─────────────┘                            │
│        │                                                     │
│   ┌────┴────┐                                               │
│   │ Caller  │                                               │
│   └─────────┘                                               │
└─────────────────────────────────────────────────────────────┘
```

**Audio pipeline:**
1. Twilio sends 8kHz μ-law → Gateway decodes to 16kHz PCM
2. PCM streamed to Deepgram Nova-3 via WebSocket
3. Nova-3 returns transcript events (partial + final)
4. Transcript fed to Azure OpenAI (GPT-4o-mini)
5. LLM response streamed to Deepgram Aura TTS
6. Aura returns 24kHz PCM → Gateway encodes to 8kHz μ-law → Twilio

**Latency budget:**
| Step | Latency | Source |
|------|---------|--------|
| Twilio → Gateway | 20-40ms | Network |
| Gateway → Deepgram STT | 50-100ms | WebSocket + first partial |
| Deepgram STT → LLM | 100-200ms | Azure OpenAI TTFT |
| LLM → Deepgram TTS | 50-100ms | Aura TTFB |
| Deepgram TTS → Twilio | 20-40ms | Network |
| **Total round-trip** | **~400-600ms** | Perceived as "instant" |

Ref: SigArch 2026 latency target <800ms for human-acceptable conversation [^16].

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEEPGRAM_API_KEY` | Yes | — | Deepgram API key |
| `DEEPGRAM_STT_MODEL` | No | `nova-3` | STT model |
| `DEEPGRAM_STT_LANGUAGE` | No | `en-US` | Language code |
| `DEEPGRAM_TTS_MODEL` | No | `aura` | TTS model |
| `DEEPGRAM_TTS_VOICE` | No | `aura-asteria-en` | Voice ID |
| `DEEPGRAM_VAD_TURNOFF` | No | `300` | Silence ms = utterance end |

### Voices Available (Aura)

| Voice ID | Gender | Tone | Best for |
|----------|--------|------|----------|
| `aura-asteria-en` | Female | Professional, warm | General reception |
| `aura-luna-en` | Female | Friendly, energetic | Customer service |
| `aura-stella-en` | Female | Calm, authoritative | Emergency triage |
| `aura-orion-en` | Male | Professional, direct | Technical/contractor |
| `aura-arcas-en` | Male | Warm, approachable | Estimates/sales |

**Recommendation for construction:** `aura-asteria-en` for day-to-day, `aura-stella-en` for emergency calls (calm authority reduces caller panic).

---

## Code Usage

### Direct API (no SDK)

```python
from src.config import DeepgramConfig
from src.infrastructure.deepgram_client import DeepgramSTT, DeepgramTTS

config = DeepgramConfig(
    api_key="your-deepgram-api-key",
    stt_model="nova-3",
    tts_voice="aura-asteria-en",
)

# STT
stt = DeepgramSTT(config)
async for event in stt.stream_audio(audio_chunks):
    if event.is_final:
        print(f"Transcript: {event.text} (confidence: {event.confidence})")

# TTS
tts = DeepgramTTS(config)
audio_bytes = await tts.synthesize("Your appointment is confirmed for tomorrow at 10 AM.")
```

### With Construction Receptionist

```python
from src.receptionist.construction_service import ConstructionReceptionist
from src.receptionist.service import ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry
from src.infrastructure.deepgram_client import DeepgramSTT, DeepgramTTS, DeepgramConfig
from src.config import OpenAIConfig

# Configs
dg_config = DeepgramConfig(api_key="dg-key", tts_voice="aura-asteria-en")
openai_config = OpenAIConfig(endpoint="...", key="...")

# Providers
stt = DeepgramSTT(dg_config)
tts = DeepgramTTS(dg_config)

# Receptionist
registry = ToolRegistry()
# ... register tools ...

receptionist = ConstructionReceptionist(
    config=ReceptionistConfig(company_name="BuildPro"),
    tool_registry=registry,
    llm_client=openai_client,
    tts_provider=tts,
)
```

---

## Deployment

### Azure Container Apps

The Bicep template (`main-construction.bicep`) already provisions a secret slot for `deepgram-api-key`. During deployment:

```bash
export DEEPGRAM_API_KEY="your-deepgram-api-key"
./scripts/deploy-construction.sh aca prod eastus
```

The script will:
1. Store the key in Azure Key Vault
2. Inject it into the Container App as a secret
3. Set `DEEPGRAM_API_KEY` environment variable

### Kubernetes

Add to your `construction-receptionist-secrets`:

```bash
kubectl create secret generic construction-receptionist-secrets \
  --from-literal=azure-openai-key="..." \
  --from-literal=twilio-account-sid="..." \
  --from-literal=twilio-auth-token="..." \
  --from-literal=deepgram-api-key="..." \
  -n construction-receptionist
```

---

## Fallback Strategy

If Deepgram fails (rate limit, outage), fall back to Azure Speech Services:

```python
async def transcribe_with_fallback(audio):
    try:
        return await deepgram_stt.stream_audio(audio)
    except DeepgramError:
        # Fallback to Azure Speech
        return await azure_speech_stt.stream_audio(audio)
```

Azure Speech Services is provisioned in the Bicep template as a backup.

---

## Cost Estimation

**@ 50 concurrent calls, 8 hours/day, 22 business days/month:**

| Service | Usage | Rate | Monthly Cost |
|---------|-------|------|-------------|
| Deepgram Nova-3 STT | 8,800 min/mo | $0.0043/min | **$38** |
| Deepgram Aura TTS | 8,800 min/mo | $0.0150/min | **$132** |
| Azure OpenAI GPT-4o-mini | ~50K calls | $0.15/1M tokens | **~$15** |
| Azure Container Apps | 2-10 replicas | $0.000024/vCPU/s | **~$80** |
| **Total** | | | **~$265/mo** |

Compare to self-hosted GPU (A10G @ $1.35/hr × 24 × 30 = **$972/mo** per GPU instance).

---

## References

- [^6]: Deepgram. (2024). Nova-3: Next-Generation Speech-to-Text.
- [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
- [^44]: Microsoft. (2024). Azure Well-Architected Framework.
- Deepgram Docs: developers.deepgram.com/docs/nova-3
- Deepgram Aura: developers.deepgram.com/docs/tts
