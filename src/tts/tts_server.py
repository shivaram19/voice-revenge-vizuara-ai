"""
TTS Service FastAPI Stub
Production: Wraps Piper TTS with streaming audio output.
Ref: ADR-004; Hansen 2023.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="TTS Service", version="0.1.0")


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "en_US-lessac-high"
    speaker_id: int = 0
    length_scale: float = 1.0


class SynthesizeResponse(BaseModel):
    audio_base64: str
    sample_rate: int = 24000
    duration_ms: int = 1000


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ready"}


@app.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(req: SynthesizeRequest) -> SynthesizeResponse:
    """Synchronous synthesis endpoint."""
    # TODO: Integrate Piper TTS model
    return SynthesizeResponse(
        audio_base64="[TTS stub: base64 audio]",
        sample_rate=24000,
        duration_ms=len(req.text) * 80,
    )
