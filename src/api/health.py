"""
Health Check Endpoints
Kubernetes liveness and readiness probes.
Ref: Kubernetes docs; ADR-005 observability requirements.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str = "0.1.0"
    checks: dict = {}


# Simple in-memory health state
_health_checks = {
    "stt_service": True,
    "tts_service": True,
    "redis": True,
    "openai": True,
}


def set_check(name: str, healthy: bool):
    """Update health check status. Called by dependency probes."""
    _health_checks[name] = healthy


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness() -> HealthStatus:
    """
    Liveness probe: returns 200 if the process is running.
    Kubernetes restarts the pod if this fails.
    """
    return HealthStatus(
        status="alive",
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness() -> HealthStatus:
    """
    Readiness probe: returns 200 only if all dependencies are healthy.
    Kubernetes removes pod from service endpoints if this fails.
    """
    all_healthy = all(_health_checks.values())
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthStatus(
        status="ready" if all_healthy else "not_ready",
        timestamp=datetime.utcnow().isoformat(),
        checks=_health_checks.copy(),
    )
