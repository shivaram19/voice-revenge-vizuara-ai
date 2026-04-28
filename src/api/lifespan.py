"""
FastAPI Lifespan — Startup / Shutdown Hooks
SRP: ONLY manages application lifecycle. No routing, no business logic.
OCP: Domains are auto-discovered; new verticals require zero changes here.
Ref: FastAPI docs; ADR-005; ADR-009.
"""

import os
import pkgutil
import importlib
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI

from src.infrastructure.azure_config import AzureConfig
from src.telephony.twilio_gateway import TwilioGateway
from src.infrastructure.interfaces import DomainPort
from src.domains.registry import DomainRegistry
from src.domains.router import DomainRouter


def _discover_domains() -> List[DomainPort]:
    """
    Auto-discover DomainPort implementations in src/domains/.
    OCP: Adding a new domain = new folder in src/domains/ — zero core changes.
    Ref: Martin 2002 (OCP) [^94]; Fowler 2018 (Convention over Configuration) [^F1].
    Meyer 1988 (Fail Fast) [^M1]: Catch specific exceptions only.
    """
    discovered: List[DomainPort] = []
    domains_pkg = importlib.import_module("src.domains")
    for _, name, ispkg in pkgutil.iter_modules(domains_pkg.__path__):
        # Skip infrastructure modules (registry, router)
        if not ispkg or name in ("registry", "router"):
            continue
        try:
            # Import the .domain submodule explicitly to avoid triggering
            # __init__.py re-exports that may cause circular imports.
            module = importlib.import_module(f"src.domains.{name}.domain")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, DomainPort)
                    and attr is not DomainPort
                    and not getattr(attr, "__abstractmethods__", None)
                ):
                    discovered.append(attr())
        except ImportError as e:
            print(f"  [WARN] Could not import domain '{name}.domain': {e}")
        except AttributeError as e:
            print(f"  [WARN] Domain '{name}' missing expected attributes: {e}")
    return discovered


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    config = AzureConfig.from_env()
    missing = config.validate()

    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    if missing and not demo_mode:
        raise RuntimeError(f"Missing required config: {', '.join(missing)}")
    if demo_mode and missing:
        print(f"[WARN] DEMO_MODE active. Missing configs: {', '.join(missing)}")

    app.state.config = config
    app.state.telephony = TwilioGateway()

    # Domain plugin registry — ADR-009
    # OCP: auto-discover domains instead of hardcoding imports [^94]
    domain_registry = DomainRegistry()
    for domain in _discover_domains():
        domain_registry.register(domain)

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
        from src.infrastructure.demo_stt_deepgram import DemoSTTDeepgram
        from src.infrastructure.deepgram_tts_client import DeepgramTTSClient
        from src.infrastructure.azure_openai_client import AzureOpenAILLMClient
        from src.emotion.tts_prosody import TTSProsodyMapper

        app.state.demo_pipeline = ProductionPipeline(
            domain_registry=domain_registry,
            domain_router=domain_router,
            gateway=TwilioGateway(),
            stt=DemoSTTDeepgram(language="en-IN"),
            tts=DeepgramTTSClient(),
            prosody_mapper=TTSProsodyMapper(),
            llm_factory=AzureOpenAILLMClient,
            deepgram_api_key=os.getenv("DEEPGRAM_API_KEY", ""),
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
