"""Conformance levels and result types."""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ConformanceLevel(str, Enum):
    STRUCTURAL = "structural"
    OPERATIONAL = "operational"
    SEMANTIC = "semantic"


class ConformanceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class ConformanceResult:
    status: ConformanceStatus
    level: ConformanceLevel
    message: str = ""
    failure: Optional["FailureReason"] = None

    @property
    def ok(self) -> bool:
        return self.status == ConformanceStatus.PASS