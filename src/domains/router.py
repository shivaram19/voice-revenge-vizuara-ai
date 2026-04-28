"""
Domain Router

Resolves the active domain for an incoming call based on phone number
or an explicitly requested domain_id. Keeps the pipeline core agnostic
to per-tenant routing rules.

Ref: Martin 2002 (OCP/DIP) [^94];
     Gamma et al. 1994 (Strategy Pattern) [^95].
"""

import json
import logging
import os
from typing import Dict, Optional

from src.infrastructure.interfaces import DomainPort
from src.domains.registry import DomainRegistry

logger = logging.getLogger(__name__)

_ENV_DOMAIN_PHONE_MAPPING = "DOMAIN_PHONE_MAPPING"
_ENV_DEFAULT_DOMAIN = "DEFAULT_DOMAIN"


class DomainRouter:
    """
    Router that resolves ``domain_id`` → :class:`DomainPort`.

    Resolution order (first match wins):

        1. **Explicit override** — caller supplies ``domain_id`` directly.
        2. **Phone-number lookup** — ``DOMAIN_PHONE_MAPPING`` env var
           (JSON dict ``{"+1234567890": "construction"}``) is parsed
           and matched against the incoming ``phone_number``.
        3. **Default fallback** — ``DEFAULT_DOMAIN`` env var.

    If no resolution succeeds, :meth:`resolve` returns ``None``,
    allowing the caller to handle the error or apply a hard-coded
    fallback.

    Usage::

        router = DomainRouter(registry)
        domain = router.resolve(phone_number="+1234567890")
        domain = router.resolve(domain_id="education")

    Ref: Martin 2002 (OCP/DIP) [^94];
         Gamma et al. 1994 (Strategy Pattern) [^95].
    """

    def __init__(self, registry: DomainRegistry) -> None:
        """
        Initialise the router with a :class:`DomainRegistry`.

        Args:
            registry: Populated registry of domain plugins.
        """
        self._registry = registry
        self._phone_map: Dict[str, str] = self._load_phone_mapping()
        self._default_domain: Optional[str] = os.getenv(_ENV_DEFAULT_DOMAIN)

    def _load_phone_mapping(self) -> Dict[str, str]:
        """
        Parse ``DOMAIN_PHONE_MAPPING`` from the environment.

        Returns:
            Dict mapping phone numbers (str) to domain_ids (str).
            Returns an empty dict if the env var is missing or invalid.
        """
        raw = os.getenv(_ENV_DOMAIN_PHONE_MAPPING)
        if not raw:
            return {}
        try:
            mapping = json.loads(raw)
            if not isinstance(mapping, dict):
                logger.warning(
                    "%s is not a JSON object; ignoring.", _ENV_DOMAIN_PHONE_MAPPING
                )
                return {}
            # Ensure string keys and values
            return {str(k): str(v) for k, v in mapping.items()}
        except json.JSONDecodeError as exc:
            logger.warning(
                "Failed to parse %s: %s", _ENV_DOMAIN_PHONE_MAPPING, exc
            )
            return {}

    def resolve(
        self,
        *,
        phone_number: Optional[str] = None,
        domain_id: Optional[str] = None,
    ) -> Optional[DomainPort]:
        """
        Resolve the domain for the given call context.

        Resolution precedence:
            1. ``domain_id`` if provided explicitly.
            2. ``phone_number`` looked up in ``DOMAIN_PHONE_MAPPING``.
            3. ``DEFAULT_DOMAIN`` environment variable.

        Args:
            phone_number: E.164 or local-format phone number of the
                incoming call. Used as a tenant discriminator.
            domain_id: Optional explicit override.

        Returns:
            The matching :class:`DomainPort`, or ``None`` if resolution
            fails.
        """
        resolved_id: Optional[str] = None

        if domain_id is not None:
            resolved_id = domain_id
            logger.debug("Domain resolved from explicit domain_id: %s", resolved_id)
        elif phone_number is not None and phone_number in self._phone_map:
            resolved_id = self._phone_map[phone_number]
            logger.debug(
                "Domain resolved from phone number %s → %s", phone_number, resolved_id
            )
        elif self._default_domain is not None:
            resolved_id = self._default_domain
            logger.debug("Domain resolved from default: %s", resolved_id)

        if resolved_id is None:
            logger.warning(
                "Could not resolve domain (phone=%s, domain_id=%s)",
                phone_number,
                domain_id,
            )
            return None

        domain = self._registry.get(resolved_id)
        if domain is None:
            logger.error(
                "Resolved domain_id '%s' is not registered in the domain registry",
                resolved_id,
            )
        return domain


# References
# [^94]: Martin, R. C. (2002). Agile Software Development, Principles, Patterns, and Practices. Prentice Hall.
# [^95]: Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
