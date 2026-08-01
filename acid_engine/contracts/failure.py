"""Structured failure reasons for diagnostics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class FailureReason:
    node_id: str
    contract_id: str
    property_name: str
    expected: Any
    actual: Any
    detail: str = ""
    plan_lock_ref: Optional[str] = None

    def human(self) -> str:
        return (
            f"[{self.node_id}] contract={self.contract_id} "
            f"property={self.property_name}: "
            f"expected={self.expected!r}, actual={self.actual!r}. "
            f"{self.detail}"
        )