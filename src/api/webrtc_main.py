"""
WebRTC ASR Service — Minimal FastAPI Entry Point
=================================================
A self-contained FastAPI application that exposes only the WebRTC ASR
endpoints and the Moonshine v2 streaming engine. Intended for deployment
as a GPU-backed container behind HTTPS, separate from the Twilio/voice-agent
control plane.

Ref: ADR-024 (WebRTC Transport for Self-Hosted ASR)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Load .env before other imports that read os.environ.
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))

from src.api.health import router as health_router
from src.api.webrtc_routes import router as webrtc_router
from src.infrastructure.logging_config import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
    logger = get_logger("webrtc.lifespan")

    from src.asr.moonshine_engine import MoonshineStreamingEngine
    from src.api.webrtc_handler import close_all_sessions

    try:
        app.state.moonshine_engine = await MoonshineStreamingEngine.create(
            language=os.getenv("MOONSHINE_LANGUAGE", "en"),
            update_interval_ms=int(os.getenv("MOONSHINE_UPDATE_INTERVAL_MS", "500")),
        )
        logger.info("moonshine_engine_ready")
    except Exception as exc:
        logger.error("moonshine_engine_init_failed", error=str(exc))
        app.state.moonshine_engine = None

    yield

    await close_all_sessions()
    if app.state.moonshine_engine is not None:
        await app.state.moonshine_engine.close()
    logger.info("webrtc_service_shutdown")


app = FastAPI(
    title="Moonshine v2 WebRTC ASR",
    description="Self-hosted real-time speech recognition via WebRTC",
    version="0.1.0",
    lifespan=lifespan,
)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(health_router)
app.include_router(webrtc_router)
