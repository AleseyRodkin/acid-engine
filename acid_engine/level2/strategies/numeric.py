"""Numeric constraint strategies."""
from __future__ import annotations
from typing import Any
from acid_engine.level2.strategies.base import ConstraintStrategy


class MinValueStrategy(ConstraintStrategy):
    """For max_latency-like constraints: effective = min(parent, child)."""

    def merge(self, parent: Any, child: Any) -> Any:
        if parent is None:
            return child
        if child is None:
            return parent
        return min(parent, child)

    def validate(self, value: Any) -> bool:
        return value is None or isinstance(value, (int, float))

    def compare_provided_required(self, provided: Any, required: Any) -> bool:
        if required is None:
            return True
        if provided is None:
            return False
        return provided <= required


class MaxValueStrategy(ConstraintStrategy):
    """For min_quality-like constraints: effective = max(parent, child)."""

    def merge(self, parent: Any, child: Any) -> Any:
        if parent is None:
            return child
        if child is None:
            return parent
        return max(parent, child)

    def validate(self, value: Any) -> bool:
        return value is None or isinstance(value, (int, float))

    def compare_provided_required(self, provided: Any, required: Any) -> bool:
        if required is None:
            return True
        if provided is None:
            return False
        return provided >= required