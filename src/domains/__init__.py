"""
Domain plugin infrastructure.

Exports the core registry and router for domain-port resolution,
enabling vertical domains to plug into the voice agent pipeline
without modifying core service code.

Ref: Cockburn 2005 (Hexagonal Architecture) [^42];
     Martin 2002 (OCP/DIP) [^94];
     Gamma et al. 1994 (Strategy Pattern) [^95].

ADR-009: Domain-Modular Voice Agent Platform.
"""

from .registry import DomainRegistry
from .router import DomainRouter

__all__ = ["DomainRegistry", "DomainRouter"]
