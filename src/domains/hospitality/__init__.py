"""
Hospitality Domain Plugin for the Voice Agent Platform.

Exports the HospitalityDomain implementation for registration with
DomainRegistry. Follows the domain-modular pattern defined in ADR-009.

Ref: Cockburn 2005 (Hexagonal Architecture) [^42];
     Martin 2002 (OCP/DIP) [^94];
     Gamma et al. 1994 (Strategy Pattern) [^95].
"""

from .domain import HospitalityDomain

__all__ = ["HospitalityDomain"]

# References
# [^42]: Cockburn, A. (2005). Hexagonal Architecture.
# [^94]: Martin, R. C. (2002). Agile Software Development, Principles, Patterns, and Practices. Prentice Hall.
# [^95]: Gamma, E., et al. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.
