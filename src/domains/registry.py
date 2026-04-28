"""
Domain Registry

Maps domain_id strings to DomainPort implementations.
Satisfies the Open/Closed Principle: new vertical domains can be
registered at runtime without modifying the pipeline core.

Ref: Martin 2002 (OCP/DIP — open for extension, closed for modification) [^94];
     Gamma et al. 1994 (Strategy Pattern — interchangeable algorithms) [^95].
"""

import logging
from typing import Dict, List, Optional

from src.infrastructure.interfaces import DomainPort

logger = logging.getLogger(__name__)


class DomainRegistry:
    """
    Registry for DomainPort implementations.

    Each vertical domain (e.g., 'construction', 'education', 'pharma')
    registers itself under a unique ``domain_id``. The pipeline queries
    the registry to locate the correct domain plugin for a given call.

    Usage::

        registry = DomainRegistry()
        registry.register(ConstructionDomain())
        registry.register(EducationDomain())
        domain = registry.get("construction")
        ids = registry.list_domains()

    Design rationale:
        - Decouples domain discovery from domain execution.
        - Allows hot-loading of domain plugins in containerised
          deployments (ADR-009).

    Ref: Martin 2002 (OCP/DIP) [^94];
         Gamma et al. 1994 (Strategy Pattern) [^95].
    """

    def __init__(self) -> None:
        self._domains: Dict[str, DomainPort] = {}

    def register(self, domain: DomainPort) -> "DomainRegistry":
        """
        Register a DomainPort implementation.

        Args:
            domain: An instance satisfying the DomainPort interface.

        Returns:
            The registry instance (chainable).

        Raises:
            ValueError: If a domain with the same ``domain_id`` is
                already registered.
        """
        domain_id = domain.domain_id
        if domain_id in self._domains:
            raise ValueError(f"Domain '{domain_id}' already registered")
        self._domains[domain_id] = domain
        logger.debug("Registered domain: %s", domain_id)
        return self

    def unregister(self, domain_id: str) -> "DomainRegistry":
        """
        Remove a domain from the registry.

        Args:
            domain_id: The unique identifier of the domain to remove.

        Returns:
            The registry instance (chainable).
        """
        if domain_id in self._domains:
            del self._domains[domain_id]
            logger.debug("Unregistered domain: %s", domain_id)
        return self

    def get(self, domain_id: str) -> Optional[DomainPort]:
        """
        Retrieve a DomainPort by its ``domain_id``.

        Args:
            domain_id: The unique domain identifier.

        Returns:
            The registered DomainPort, or ``None`` if not found.
        """
        return self._domains.get(domain_id)

    def list_domains(self) -> List[str]:
        """
        Return a sorted list of all registered domain identifiers.

        Returns:
            List of ``domain_id`` strings.
        """
        return sorted(self._domains.keys())

    def __contains__(self, domain_id: str) -> bool:
        return domain_id in self._domains

    def __len__(self) -> int:
        return len(self._domains)


# References
# [^94]: Martin, R. C. (2002). Agile Software Development, Principles, Patterns, and Practices. Prentice Hall.
# [^95]: Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
