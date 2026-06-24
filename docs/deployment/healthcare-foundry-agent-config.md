# Healthcare MVP — Azure AI Foundry Agent Configuration

Use these values when creating the agent in Azure AI Foundry.

---

## General

| Field | Recommended value | Why |
|-------|-------------------|-----|
| **Display name** | `Arogya Hospital Follow-Up Agent` | Clear, hospital-branded name visible to stakeholders. |
| **Description** | `Post-visit voice agent that checks patient well-being, medicine adherence, and side effects. Supports Telugu-English code-switching and escalates emergencies.` | Tells others the scope and safety intent. |

---

## Starter prompts

These are example opening lines a tester can click to start a conversation. Keep them short and realistic.

1. `Hello, I am Ramesh. I am feeling okay.`
2. `Namaste, nenu Lakshmi. Naku konchem headache undi.`
3. `Hi, this is Kiran. I forgot my morning medicine.`

---

## Voice mode

| Field | Recommended value | Why |
|-------|-------------------|-----|
| **Speech input** | Enabled | Required for phone-style conversation. |
| **Speech recognition model** | Azure Speech | Foundry default; good English + code-mixed recognition. |
| **Create custom speech** | Optional for later | Use only if medical Telugu terms (e.g., medicine names) are frequently misrecognized. |
| **Language** | Auto-detect | Lets Telugu-English bilingual patients speak naturally. If Auto-detect causes issues, pin to `Telugu (India)` for Telugu-first patients or `English (India)` for English-first patients. |

---

## Advanced settings — Speech input

| Field | Recommended value | Why |
|-------|-------------------|-----|
| **Voice Activity Detection (VAD)** | Azure Semantic VAD | Better turn detection for natural speech with pauses. |
| **End of utterance (EOU)** | Default / Medium | Elderly patients may pause longer; medium gives them time without cutting them off. |
| **Audio enhancement** | Enable noise suppression + echo cancellation | Improves quality over phone speakers and noisy environments. |
| **Phrase list** | Add the seeded medicine names and symptom terms below | Boosts recognition accuracy for domain-specific words. |

### Suggested phrase list

Add one phrase per line. Mix English and Telugu as needed:

```text
Telma H
Metformin
Combiflam
Azithromycin
headache
chest pain
breathing trouble
nausea
fever
mild
severe
Tablets teesukuntunna
Naku headache undi
Naku fever undi
```

---

## Speech output

| Field | Recommended value | Why |
|-------|-------------------|-----|
| **Voice** | `Ava Dragon HD Latest` (Female) | Warm, clear English voice. Good for English and Telugu-English callers. |
| **Custom voice** | Optional | Only if you record a branded Telugu/English hospital voice later. |

> **Note on Telugu output:** If the patient speaks Telugu and the model replies in Telugu, an English voice will phonetically render Telugu words. For a fully Telugu experience, select an Azure Telugu neural voice if Foundry offers one (e.g., `te-IN-PriyaNeural` or `te-IN-MohanNeural`).

---

## Interim response

| Field | Recommended value | Why |
|-------|-------------------|-----|
| **Type** | LLM-generated messages | Keeps the agent conversational rather than fixed fillers. |
| **Response threshold** | 500 ms | Default. Lower if you want faster acknowledgment; raise if the model is too eager. |

---

## Proactive engagement

| Field | Recommended value | Why |
|-------|-------------------|-----|
| **Proactive engagement** | Enabled | The agent should greet first: "Hello Ramesh, namaste. This is Dr. Priya from Arogya Hospital. Is this a good time to talk?" |

---

## Avatar

| Field | Recommended value | Why |
|-------|-------------------|-----|
| **Avatar** | None / disabled | This MVP is voice-first (phone/browser audio). Avatar is not needed unless you later add a video kiosk. |

---

## Instructions tab

Paste the optimized instructions from:

```
docs/deployment/healthcare-foundry-instructions.md
```

---

## Knowledge / tools tab

- **Knowledge:** Not required for MVP. The patient context is injected per call via the local CLI script.
- **Tools:** If Foundry supports function calling, you can optionally register the healthcare tools from `src/domains/healthcare_mvp/tools.py`. The current `scripts/run_healthcare_voicelive.py` already wires them when running locally.

---

## Deployment / testing checklist

1. Create the agent with the settings above.
2. Paste the instructions from `healthcare-foundry-instructions.md`.
3. Test with the starter prompts.
4. Try a safety escalation: type or say "I have severe chest pain" — the agent should immediately tell you to go to the emergency department.
5. Try Telugu-English mixing: "Naku konchem headache undi."
6. Verify the agent never diagnoses or changes medicine instructions.
