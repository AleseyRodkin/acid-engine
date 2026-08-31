"""ExecutionState — current status of execution, separate from data."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionState:
    """Mutable runtime status (not part of immutable snapshot)."""
    status: ExecutionStatus = ExecutionStatus.PENDING
    error_message: str | None = None

    def mark_running(self) -> None:
        self.status = ExecutionStatus.RUNNING

    def mark_completed(self) -> None:
        self.status = ExecutionStatus.COMPLETED

    def mark_failed(self, msg: str) -> None:
        self.status = ExecutionStatus.FAILED
        self.error_message = msg

    def mark_skipped(self) -> None:
        self.status = ExecutionStatus.SKIPPED