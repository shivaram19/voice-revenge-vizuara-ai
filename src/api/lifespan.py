"""
FastAPI Lifespan — Startup / Shutdown Hooks
SRP: ONLY manages application lifecycle. No routing, no business logic.
Ref: FastAPI docs; ADR-005.
"""

import os
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

    # Demo mode: allow missing Azure OpenAI / Redis if only Twilio is present.
    # This supports sales demos where the full AI pipeline is not yet wired.
    # Ref: ADR-005 notes fallback to message-taking when LLM is unavailable.
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    if missing and not demo_mode:
        raise RuntimeError(f"Missing required config: {', '.join(missing)}")
    if demo_mode and missing:
        print(f"[WARN] DEMO_MODE active. Missing configs: {', '.join(missing)}")

    app.state.config = config
    app.state.telephony = TwilioGateway()

    # Domain plugin registry — ADR-009
    from src.domains.registry import DomainRegistry
    from src.domains.router import DomainRouter
    from src.domains.construction import ConstructionDomain
    from src.domains.education import EducationDomain

    domain_registry = DomainRegistry()
    domain_registry.register(ConstructionDomain())
    domain_registry.register(EducationDomain())
    domain_router = DomainRouter(domain_registry)

    app.state.domain_registry = domain_registry
    app.state.domain_router = domain_router

    print(f"  Registered domains: {domain_registry.list_domains()}")

    if demo_mode:
        from src.infrastructure.demo_pipeline import DemoPipeline
        app.state.demo_pipeline = DemoPipeline()
        print("  DEMO MODE: Local CPU pipeline active (faster-whisper + MockLLM + Piper)")
    else:
        from src.infrastructure.production_pipeline import ProductionPipeline
        app.state.demo_pipeline = ProductionPipeline(
            domain_registry=domain_registry,
            domain_router=domain_router,
        )
        print("  PROD MODE: Cloud pipeline active (Deepgram STT + Azure OpenAI + Aura TTS)")

    print(f"Voice Agent Controller started")
    if not demo_mode:
        print(f"  OpenAI endpoint: {config.openai_endpoint}")
        print(f"  Redis host: {config.redis_host}")
    print(f"  Twilio account: {config.twilio_account_sid[:6]}...")

    yield

    # Shutdown
    print("Voice Agent Controller shutting down...")
