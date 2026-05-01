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
from src.infrastructure.logging_config import configure_logging, get_logger
from src.infrastructure.telemetry import init_telemetry


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
            logger = get_logger("lifespan")
            logger.warning("domain_import_failed", domain=name, error=str(e))
        except AttributeError as e:
            logger = get_logger("lifespan")
            logger.warning("domain_attribute_error", domain=name, error=str(e))
    return discovered


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Logging first — everything below uses it
    configure_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
    logger = get_logger("lifespan")

    # Telemetry — OpenTelemetry + Application Insights
    telemetry = init_telemetry(service_name="voice-agent-api")
    logger.info("telemetry_initialized", enabled=telemetry.get("enabled", False))

    # Startup
    config = AzureConfig.from_env()
    missing = config.validate()

    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    if missing and not demo_mode:
        raise RuntimeError(f"Missing required config: {', '.join(missing)}")
    if demo_mode and missing:
        logger.warning("demo_mode_missing_configs", configs=missing)

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

    logger.info("domains_registered", domains=domain_registry.list_domains())

    if demo_mode:
        from src.infrastructure.demo_pipeline import DemoPipeline
        app.state.demo_pipeline = DemoPipeline()
        logger.info("demo_mode_active")
    else:
        from src.infrastructure.production_pipeline import ProductionPipeline
        from src.infrastructure.demo_stt_deepgram import DemoSTTDeepgram
        from src.infrastructure.deepgram_tts_client import DeepgramTTSClient
        from src.emotion.tts_prosody import TTSProsodyMapper
        from src.infrastructure.sarvam_tts_client import SarvamTTSClient

        # --- LLM factory: prefer Sarvam when Azure keys are absent ---
        azure_key      = os.getenv("AZURE_OPENAI_KEY", "")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        sarvam_api_key = os.getenv("SARVAM_API_KEY", "")

        if azure_key and azure_endpoint:
            from src.infrastructure.azure_openai_client import AzureOpenAILLMClient
            llm_factory = AzureOpenAILLMClient
            logger.info("llm_provider", provider="azure_openai")
        elif sarvam_api_key:
            from src.infrastructure.sarvam_llm_client import SarvamLLMClient
            llm_factory = SarvamLLMClient
            logger.info("llm_provider", provider="sarvam_m")
        else:
            raise RuntimeError(
                "No LLM configured. Set either AZURE_OPENAI_KEY + AZURE_OPENAI_ENDPOINT "
                "or SARVAM_API_KEY."
            )

        # --- Sarvam TTS for Telugu sessions ---
        sarvam_tts = None
        if sarvam_api_key:
            try:
                sarvam_tts = SarvamTTSClient(
                    api_key=sarvam_api_key,
                    language_code="te-IN",
                    gender="female",
                )
                logger.info("sarvam_tts_initialized", language="te-IN", speaker="kavya")
            except Exception as e:
                logger.warning("sarvam_tts_init_failed", error=str(e))
        else:
            logger.info("sarvam_tts_disabled", reason="SARVAM_API_KEY not set")

        app.state.demo_pipeline = ProductionPipeline(
            domain_registry=domain_registry,
            domain_router=domain_router,
            gateway=TwilioGateway(),
            stt=DemoSTTDeepgram(language="en-IN"),
            tts=DeepgramTTSClient(),
            prosody_mapper=TTSProsodyMapper(),
            llm_factory=llm_factory,
            deepgram_api_key=os.getenv("DEEPGRAM_API_KEY", ""),
            sarvam_tts=sarvam_tts,
        )
        logger.info("prod_mode_active")

    logger.info("voice_agent_started")
    if not demo_mode:
        logger.info(
            "config_summary",
            openai_endpoint=config.openai_endpoint,
            redis_host=config.redis_host,
            twilio_account=config.twilio_account_sid[:6],
        )

    yield

    # Shutdown
    logger.info("voice_agent_shutting_down")
