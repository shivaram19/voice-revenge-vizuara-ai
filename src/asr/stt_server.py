"""
STT Service FastAPI Stub
Production: Wraps faster-whisper with streaming gRPC/HTTP.
Ref: ADR-002; Gandhi et al. 2023.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="STT Service", version="0.1.0")


class TranscribeRequest(BaseModel):
    audio_base64: str
    language: str = "en"
    vad_filter: bool = True


class TranscriptResponse(BaseModel):
    text: str
    is_final: bool = True
    confidence: float = 0.95
    language: str = "en"


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ready"}


@app.post("/transcribe", response_model=TranscriptResponse)
async def transcribe(req: TranscribeRequest) -> TranscriptResponse:
    """Synchronous transcription endpoint."""
    # TODO: Integrate faster-whisper model
    return TranscriptResponse(
        text="[STT stub: transcribed text]",
        is_final=True,
        confidence=0.95,
        language=req.language,
    )
