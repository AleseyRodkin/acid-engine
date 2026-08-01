"""ConstraintResolver — core contract resolution engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from acid_engine.contracts.strategies.base import ConstraintStrategy
from acid_engine.contracts.strategies.numeric import MinValueStrategy, MaxValueStrategy
from acid_engine.contracts.strategies.set_ops import IntersectionStrategy, UnionStrategy
from acid_engine.contracts.strategies.boolean_policy import BooleanStrengthenStrategy
from acid_engine.contracts.strategies.string_enum import StringEnumStrategy

@dataclass
class ResolveConflict(Exception):
    field_name: str
    parent_value: Any
    child_value: Any
    message: str = ""

    def __str__(self) -> str:
        return (
            f"Conflict on {self.field_name}: "
            f"parent={self.parent_value!r}, child={self.child_value!r}. "
            f"{self.message}"
        )


DEFAULT_STRATEGIES: Dict[str, ConstraintStrategy] = {
    "max_latency_ms": MinValueStrategy(),
    "min_quality": MaxValueStrategy(),
    "quality_gate": MaxValueStrategy(),
    "allowed_domains": IntersectionStrategy(),
    "forbidden_effects": UnionStrategy(),
    "pure": BooleanStrengthenStrategy(),
    "history": StringEnumStrategy(("none", "compact", "full")),
    "network": StringEnumStrategy(("allowed", "forbidden")),
    "security": StringEnumStrategy(("permissive", "restricted")),
}


@dataclass
class ConstraintResolver:
    """
    Declared + Inherited + Defaults → Effective.
    Single public entry point; strategies are pluggable.
    """
    strategies: Dict[str, ConstraintStrategy] = field(
        default_factory=lambda: dict(DEFAULT_STRATEGIES)
    )

    def resolve_field(
        self,
        field_name: str,
        parent: Any,
        child: Any,
        default: Any = None,
    ) -> Any:
        strategy = self.strategies.get(field_name)
        if strategy is None:
            # fallback: child overrides parent if present
            if child is not None:
                return child
            if parent is not None:
                return parent
            return default

        # Conflict detection for boolean strengthen
        if isinstance(strategy, BooleanStrengthenStrategy):
            if strategy.detect_conflict(parent, child):
                raise ResolveConflict(
                    field_name=field_name,
                    parent_value=parent,
                    child_value=child,
                    message="Child cannot weaken pure=True to False",
                )

        effective = strategy.merge(parent, child)
        if effective is None:
            effective = default
        return effective

    def resolve_policy(
        self,
        parent_policy: dict,
        child_policy: dict,
        defaults: Optional[dict] = None,
    ) -> dict:
        defaults = defaults or {}
        keys = set(parent_policy) | set(child_policy) | set(defaults)
        result = {}
        for k in keys:
            result[k] = self.resolve_field(
                k,
                parent_policy.get(k),
                child_policy.get(k),
                defaults.get(k),
            )
        return result