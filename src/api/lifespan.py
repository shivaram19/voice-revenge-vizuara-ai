"""
FastAPI Lifespan — Startup / Shutdown Hooks
SRP: ONLY manages application lifecycle. No routing, no business logic.
Ref: FastAPI docs; ADR-005.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.infrastructure.azure_config import AzureConfig
from src.telephony.twilio_gateway import TwilioGateway


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    config = AzureConfig.from_env()
    missing = config.validate()
    if missing:
        raise RuntimeError(f"Missing required config: {', '.join(missing)}")

    app.state.config = config
    app.state.telephony = TwilioGateway()

    print(f"Voice Agent Controller started")
    print(f"  OpenAI endpoint: {config.openai_endpoint}")
    print(f"  Redis host: {config.redis_host}")

    yield

    # Shutdown
    print("Voice Agent Controller shutting down...")
