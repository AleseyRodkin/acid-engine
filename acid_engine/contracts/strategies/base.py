"""Base constraint strategy interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class ConstraintStrategy(ABC):
    @abstractmethod
    def merge(self, parent: Any, child: Any) -> Any:
        """Merge parent and child values into effective value."""

    @abstractmethod
    def validate(self, value: Any) -> bool:
        """Validate a single value."""

    def compare_provided_required(self, provided: Any, required: Any) -> bool:
        """Default: provided must equal required. Override as needed."""
        return provided == required