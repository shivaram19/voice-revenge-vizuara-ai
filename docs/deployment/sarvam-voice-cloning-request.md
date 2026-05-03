# Sarvam Enterprise Voice Cloning — Request Package

**Prepared for:** developer@sarvam.ai  
**From:** TreloLabs / Jaya High School, Suryapet  
**Date:** 2026-05-02  

---

## 1. Who We Are

**TreloLabs** is building a production voice agent platform for Indian educational institutions. Our first deployment is **Jaya High School, Suryapet, Telangana** — a Telugu-medium school serving rural Telangana families.

We are currently using Sarvam Bulbul v3 with speaker `kavitha` for Telugu TTS. The voice quality is excellent, but the pronunciation of regional Telangana words does not match the local dialect our parent community expects.

## 2. What We Need

**Custom speaker cloning** for Bulbul v3 with the following characteristics:

| Requirement | Detail |
|---|---|
| **Target language** | Telugu (`te-IN`) with English code-mixing |
| **Target domain** | School fee confirmation phone calls |
| **Tone** | Warm, respectful, professional (school admin register) |
| **Dialect** | Telangana rural (Suryapet region) — NOT generic pan-Indian Telugu |
| **Output sample rate** | 8000 Hz (PSTN telephony standard) and 24000 Hz |
| **Use case volume** | 1,000–5,000 calls/month initially, scaling to 50,000+ |

## 3. What We Can Provide

### 3.1 Voice Recordings
- **30+ minutes** of studio-quality speech from a native Suryapet speaker
- Content: Telugu-English code-mixed sentences covering our call scripts
- Format: 48kHz WAV, mono, 24-bit (or your preferred format)

### 3.2 Script Content
Our typical call script includes:
- Greetings: "Namaskaaram sir, nenu Jaya High School nunchi matlardhanam"
- Fee confirmations: "Aarav term one fees kattesaru, confirm cheyyadaniki call chesam"
- Closings: "In case of any queries, contact Jaya High School, sir"

### 3.3 Pronunciation Guide
- JSON dictionary of 50+ words with preferred spoken forms
- IPA or phonetic transcriptions for key dialect words

## 4. Questions for Sarvam

1. **Timeline:** How long from recording submission to deployed speaker ID?
2. **Pricing:** One-time setup fee + per-call API cost structure?
3. **Format:** What recording format, duration, and environment do you require?
4. **Code-mixing:** Does the cloned speaker handle intra-sentence Telugu-English switching natively?
5. **Updates:** Can we refine the speaker with additional recordings post-deployment?
6. **SLA:** Uptime guarantee for the custom speaker endpoint?

## 5. Contact

**Technical lead:** [Your name]  
**Email:** [Your email]  
**Phone:** +91 [Your phone]  

Ready to begin recordings immediately upon confirmation of requirements.

---

*Attachment: Sample recording script (pronunciation_dicts/suryapet_recording_script.md)*
