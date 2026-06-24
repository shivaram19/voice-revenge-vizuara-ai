"""
Healthcare MVP — Standalone Voice Agent Service
===============================================
A minimal FastAPI application for the hospital patient follow-up MVP.
Runs independently of the legacy TreloLabs voice-agent platform.

Endpoints:
  - WebRTC audio ingestion via /webrtc/offer
  - Dashboard summaries via /healthcare/dashboard/*
  - Browser demo at /static/healthcare-demo.html

Ref: docs/engineering/goal-vector-healthcare-mvp.md
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.health import router as health_router
from src.api.healthcare_dashboard import router as dashboard_router
from src.api.healthcare_webrtc_routes import router as healthcare_webrtc_router
from src.domains.healthcare_mvp.seed import set_follow_up_log_path
from src.infrastructure.logging_config import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load .env inside lifespan so environment is configured before any
    # runtime lookup (LOG_LEVEL, HEALTHCARE_FOLLOW_UP_LOG, etc.).
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path))

    configure_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
    logger = get_logger("healthcare_mvp.lifespan")

    # Configure JSONL persistence for follow-up records.
    log_path = os.getenv("HEALTHCARE_FOLLOW_UP_LOG", "./healthcare_follow_ups.jsonl")
    set_follow_up_log_path(log_path)
    logger.info("healthcare_mvp_startup", follow_up_log=log_path)

    from src.api.webrtc_handler import close_all_sessions
    from src.asr.moonshine_engine import MoonshineStreamingEngine

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
    logger.info("healthcare_mvp_shutdown")


app = FastAPI(
    title="Healthcare Patient Follow-Up MVP",
    description="Self-hosted real-time voice follow-up agent for hospitals",
    version="0.1.0",
    lifespan=lifespan,
)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(health_router)
app.include_router(healthcare_webrtc_router)
app.include_router(dashboard_router)
