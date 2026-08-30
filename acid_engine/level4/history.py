"""История запусков: запись и replay по факту записи.

Отката состояния нет — только lookup по run_id.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level2.conformance import ConformanceResult


@dataclass
class RunRecord:
    """Запись одного выполнения."""
    run_id: str
    plan_hash: str
    timestamp: float
    input_data: Any
    output_data: Any
    observation: ExecutionObservation
    success: bool
    note: str = ""


@dataclass
class HistoryStore:
    """In-memory хранилище истории. Не БД и не журнал с откатом."""
    records: List[RunRecord] = field(default_factory=list)

    def add(self, record: RunRecord) -> None:
        self.records.append(record)

    def last(self) -> Optional[RunRecord]:
        return self.records[-1] if self.records else None

    def find_by_plan(self, plan_hash: str) -> List[RunRecord]:
        return [r for r in self.records if r.plan_hash == plan_hash]


def find_record(history: HistoryStore, run_id: str) -> Optional[RunRecord]:
    """Lookup by run_id. Не восстанавливает состояние и не отменяет эффекты."""
    for r in reversed(history.records):
        if r.run_id == run_id:
            return r
    return None


def replay_from_record(
    record: RunRecord,
    script,
    expected_output: Optional[Any] = None,
    plan=None,
) -> ConformanceResult:
    """
    Переигрывает скрипт на input из записи и сверяет выход с фактом.
    Без plan.lock — SKIPPED. Не обходит bind.
    """
    if plan is None:
        return ConformanceResult.skipped(
            "replay_from_record without plan.lock is not a fact"
        )

    from acid_engine.level3.script.runner import replay_run

    target = expected_output if expected_output is not None else record.output_data
    return replay_run(plan, script, record.input_data, expected_output=target)
