"""Set constraint strategies."""
from __future__ import annotations
from typing import Any
from acid_engine.level2.strategies.base import ConstraintStrategy


class IntersectionStrategy(ConstraintStrategy):
    """allowed_domains: effective = parent ∩ child"""

    def merge(self, parent: Any, child: Any) -> Any:
        p = set(parent or [])
        c = set(child or [])
        return sorted(p & c)

    def validate(self, value: Any) -> bool:
        return value is None or isinstance(value, (list, set, tuple))

    def compare_provided_required(self, provided: Any, required: Any) -> bool:
        if not required:
            return True
        return set(provided or []).issuperset(set(required))


class UnionStrategy(ConstraintStrategy):
    """forbidden_effects: effective = parent ∪ child"""

    def merge(self, parent: Any, child: Any) -> Any:
        p = set(parent or [])
        c = set(child or [])
        return sorted(p | c)

    def validate(self, value: Any) -> bool:
        return value is None or isinstance(value, (list, set, tuple))

    def compare_provided_required(self, provided: Any, required: Any) -> bool:
        # provided effects must not intersect required forbidden
        return set(provided or []).isdisjoint(set(required or []))