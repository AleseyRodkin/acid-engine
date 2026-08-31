"""Script specification: Parameters, Policy, ImplementationRequirements."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Parameters:
    """Immutable algorithm parameters."""
    values: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def to_canonical_dict(self) -> dict[str, Any]:
        return {"values": dict(sorted(self.values.items()))}


@dataclass(frozen=True, slots=True)
class Policy:
    """Execution and governance policy."""
    pure: bool = False
    max_latency_ms: float | None = None
    history: str = "none"  # none | compact | full
    network: str = "forbidden"  # forbidden | allowed
    security: str = "restricted"
    quality_gate: float | None = None

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "pure": self.pure,
            "max_latency_ms": self.max_latency_ms,
            "history": self.history,
            "network": self.network,
            "security": self.security,
            "quality_gate": self.quality_gate,
        }


@dataclass(frozen=True, slots=True)
class ImplementationRequirements:
    """
    Requirements on the shape of implementation.
    required_order is intentionally NOT mandatory in MVP.
    """
    required_methods: tuple[str, ...] = ()
    required_exports: tuple[str, ...] = ()
    required_signatures: tuple[str, ...] = ()

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "required_methods": list(self.required_methods),
            "required_exports": list(self.required_exports),
            "required_signatures": list(self.required_signatures),
        }


@dataclass(frozen=True, slots=True)
class Specification:
    parameters: Parameters = field(default_factory=Parameters)
    policy: Policy = field(default_factory=Policy)
    implementation_requirements: ImplementationRequirements = field(
        default_factory=ImplementationRequirements
    )

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "parameters": self.parameters.to_canonical_dict(),
            "policy": self.policy.to_canonical_dict(),
            "implementation_requirements": (
                self.implementation_requirements.to_canonical_dict()
            ),
        }