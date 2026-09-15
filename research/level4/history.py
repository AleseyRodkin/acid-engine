"""Run history: record and replay from the record.

No state rollback — lookup by run_id only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acid_engine.level2.conformance import ConformanceResult
from acid_engine.level3.container.observation import ExecutionObservation


@dataclass
class RunRecord:
    """Record of one execution."""
    run_id: str
    plan_hash: str
    timestamp: float
    input_data: Any
    output_data: Any
    observation: ExecutionObservation | None
    success: bool
    note: str = ""


@dataclass
class HistoryStore:
    """In-memory history store. Not a DB and not a journal with rollback."""
    records: list[RunRecord] = field(default_factory=list)

    def add(self, record: RunRecord) -> None:
        self.records.append(record)

    def last(self) -> RunRecord | None:
        return self.records[-1] if self.records else None

    def find_by_plan(self, plan_hash: str) -> list[RunRecord]:
        return [r for r in self.records if r.plan_hash == plan_hash]


def find_record(history: HistoryStore, run_id: str) -> RunRecord | None:
    """Lookup by run_id. Does not restore state and does not undo effects."""
    for r in reversed(history.records):
        if r.run_id == run_id:
            return r
    return None


def replay_from_record(
    record: RunRecord,
    script: Any,
    expected_output: Any | None = None,
    plan: Any = None,
) -> ConformanceResult:
    """
    Re-run the script on the recorded input and check the output against the fact.
    Without plan.lock — SKIPPED. Does not bypass bind.
    """
    if plan is None:
        return ConformanceResult.skipped(
            "replay_from_record without plan.lock is not a fact"
        )

    from acid_engine.level3.script.runner import replay_run

    target = expected_output if expected_output is not None else record.output_data
    return replay_run(plan, script, record.input_data, expected_output=target)
