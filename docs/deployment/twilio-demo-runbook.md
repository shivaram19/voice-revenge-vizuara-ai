# Twilio Demo Call Runbook

> **Goal:** Verify credentials, place a recorded outbound call, and retrieve the recording to share with prospects.
>
> **Time:** 10 minutes  
> **Cost:** ~$0.05 per minute of call time  
> **Prerequisites:** Twilio account with $20 credit, one purchased phone number

---

## 1. Environment Setup

Set these in your shell (never commit them):

```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_PHONE_NUMBER="+15551234567"
```

**Research note:** Twilio REST API follows Fielding's state-transfer architecture (REST) [^79]. All resources (calls, recordings) are addressable via URI and manipulated through standard HTTP verbs.

---

## 2. Verify Credentials

```bash
python3 scripts/verify-twilio.py
```

Expected output:

```
[OK] Account SID:   AC...
[OK] Friendly Name: Your Project
[OK] Status:        active
[OK] Balance:       20.00 USD
[OK] Provisioned phone numbers: 1
       +15551234567  (voice, sms)

You are ready to make outbound demo calls.
```

If you see `[WARN] Trial account detected`, you can only call numbers you have verified in the Twilio console. Upgrade to a paid account (which you have with the $20 credit) to remove this restriction.

---

## 3. Make a Recorded Demo Call (No Live AI)

The fastest path to a shareable recording. The call plays a pre-scripted greeting and records the interaction.

```bash
python3 scripts/demo-outbound-call.py \
    --to +15559876543 \
    --from +15551234567
```

**What happens:**
1. Twilio dials the target number.
2. Upon answer, it plays a greeting using Amazon Polly neural TTS (`Polly.Joanna`).
3. Twilio starts a dual-channel recording (`record-from-answer`).
4. When the call ends, Twilio POSTs the recording URL to `/twilio/recording`.

**Citations:**
- Twilio Media Streams relay 8 kHz μ-law audio over WebSocket [^43].
- ITU-T G.711 μ-law companding is the PSTN standard [^38].
- Twilio Recording API supports dual-channel and async callback delivery [^80].

---

## 4. Retrieve the Recording

Recordings are available via:

**A. Console (easiest)**
Open: `https://console.twilio.com/us1/monitor/logs/calls`
Click your call → Recordings tab → Download.

**B. REST API**
```bash
curl -X GET "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Recordings.json" \
  -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN"
```

The `recording_url` is also printed in your application logs when the `RecordingStatusCallback` hits `/twilio/recording`.

---

## 5. Live AI Demo Call (Full Pipeline)

The WebSocket pipeline is now wired for live AI conversations with **zero API keys**.
It runs entirely on your CPU using:
- **STT**: faster-whisper `tiny` model (150 MB) [^5]
- **LLM**: MockLLM with deterministic tool routing
- **TTS**: Piper `en_US-lessac-medium` voice (60 MB) [^9]
- **Brand**: TreloLabs Voice AI (voice.trelolabs.com)

### 5a. Download models (one-time)

```bash
python3 scripts/setup-demo-models.py
```

This downloads ~210 MB of models to `models/piper/`.

### 5b. Start the server in demo mode

```bash
export DEMO_MODE=true
export TWILIO_ACCOUNT_SID="AC..."
export TWILIO_AUTH_TOKEN="..."

pip install fastapi uvicorn[standard]
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 5c. Expose via ngrok

```bash
ngrok http 8000
# Copy the https URL, e.g., https://abc123.ngrok.io
```

### 5d. Make the live call

```bash
export WEBSOCKET_URL="wss://abc123.ngrok.io/ws/twilio/inbound"

python3 scripts/demo-outbound-call.py \
    --to +15559876543 \
    --from +15551234567 \
    --websocket-url "$WEBSOCKET_URL"
```

**What happens during the call:**
1. Twilio dials your phone.
2. You hear: *"Thank you for calling TreloLabs Voice AI. I'm your virtual receptionist..."*
3. You speak (e.g., *"I need a plumber"*).
4. The server buffers your audio, detects silence, transcribes with Whisper, routes intent through the MockLLM, executes the contractor lookup tool, and synthesizes a response with Piper.
5. You hear the agent's response (e.g., *"Found 1 contractor: James O'Brien, Plumbing, phone 5550103"*).

Ref: ADR-006 documents the TreloLabs domain and branding architecture [^82][^85].

**Latency:** First response takes ~2-3 seconds (STT + LLM + TTS cold start). Subsequent turns are faster as models stay in memory.

Ref: ADR-005 documents the cascaded pipeline architecture [^16].

---

## 6. Compliance Checklist Before Sharing

> **Ethical Technologist mandate (Persona #5):** Call recording consent is not optional.

| Jurisdiction | Requirement | How to satisfy |
|--------------|-------------|----------------|
| U.S. Federal | One-party consent (18 U.S.C. § 2511) | You are a party to the call. |
| California | All-party consent | Inform recipient: "This call is being recorded." |
| EU / GDPR | Lawful basis + data subject rights | Obtain explicit consent; provide deletion mechanism. |

Twilio provides a `<Say>` hook before recording begins. Add this to your TwiML:

```xml
<Say>This call is being recorded for quality and training purposes.</Say>
<Pause length="1"/>
```

Ref: Twilio Privacy and Compliance Guide [^81].

---

## 7. One-Liner Summary

```bash
export TWILIO_ACCOUNT_SID="AC..."
export TWILIO_AUTH_TOKEN="..."
export TWILIO_PHONE_NUMBER="+15551234567"
python3 scripts/verify-twilio.py && \
python3 scripts/demo-outbound-call.py --to +15559876543 --from +15551234567
```

Then grab the recording from the Twilio console and send it.

---

*Runbook version: 1.0*  
*Established: 2026-04-27*  
*References: ADR-005, [^38], [^43], [^79], [^80], [^81]*
