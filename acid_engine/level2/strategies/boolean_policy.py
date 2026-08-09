"""Boolean policy strategy (e.g. pure)."""
from __future__ import annotations
from typing import Any
from acid_engine.level2.strategies.base import ConstraintStrategy


class BooleanStrengthenStrategy(ConstraintStrategy):
    """
    pure=true cannot be weakened to false by child.
    Effective = parent OR child (True wins / strengthens).
    """

    def merge(self, parent: Any, child: Any) -> Any:
        p = bool(parent) if parent is not None else False
        c = bool(child) if child is not None else False
        return p or c

    def validate(self, value: Any) -> bool:
        return value is None or isinstance(value, bool)

    def compare_provided_required(self, provided: Any, required: Any) -> bool:
        if not required:
            return True
        return bool(provided) is True

    def detect_conflict(self, parent: Any, child: Any) -> bool:
        """Child tries to weaken parent pure=True to False."""
        if parent is None or child is None:
            return False
        return bool(parent) is True and bool(child) is False