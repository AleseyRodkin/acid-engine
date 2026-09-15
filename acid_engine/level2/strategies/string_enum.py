"""Strategy for string fields with ordered values (strictness)."""
from __future__ import annotations

from typing import Any

from acid_engine.level2.strategies.base import ConstraintStrategy


class StringEnumStrategy(ConstraintStrategy):
    """
    For fields with a set of values ordered by strictness.
    Order: weakest (index 0) to strictest (last).
    effective = the stricter of parent and child.
    """
    def __init__(self, order: tuple[str, ...]):
        self.order = order
        self._rank = {v: i for i, v in enumerate(order)}

    def merge(self, parent: Any, child: Any) -> Any:
        p_val = parent if parent in self._rank else None
        c_val = child if child in self._rank else None
        if p_val is None and c_val is None:
            return None
        if p_val is None:
            return c_val
        if c_val is None:
            return p_val
        # higher rank = stricter
        if self._rank[p_val] >= self._rank[c_val]:
            return p_val
        return c_val

    def validate(self, value: Any) -> bool:
        return value is None or value in self._rank

    def compare_provided_required(self, provided: Any, required: Any) -> bool:
        # Provided must not be weaker than Required (rank >=)
        if required is None:
            return True
        if provided is None:
            return False
        return self._rank.get(provided, -1) >= self._rank.get(required, -1)