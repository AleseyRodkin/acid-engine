"""История запусков: запись и replay по факту записи.

Отката состояния нет — только lookup по run_id.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level2.conformance import (
    ConformanceResult,
    ConformanceStatus,
    ConformanceLevel,
    check_conformance,
)
from acid_engine.level2.failure import FailureReason


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
) -> ConformanceResult:
    """
    Переигрывает скрипт на input из записи и сверяет выход с фактом.

    Факт = expected_output, если передан, иначе record.output_data.
    Несовпадение → FAIL. Совпадение → check_conformance (тип/policy).
    """
    from acid_engine.level3.script.python_runtime import run_script
    from acid_engine.level3.container.port import PortRef
    from acid_engine.level3.container.snapshot import ContainerSnapshot

    target = expected_output if expected_output is not None else record.output_data

    in_port = PortRef(module=script.contract_id.name, direction="input", name="value")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=record.input_data,
    )
    out_snap, obs, _, _ = run_script(script, input_snap)

    if out_snap.data != target:
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.OPERATIONAL,
            message="history replay output mismatch",
            failure=FailureReason(
                node_id=script.name,
                contract_id=str(script.contract_id),
                property_name="output",
                expected=target,
                actual=out_snap.data,
                detail=f"run_id={record.run_id}",
            ),
        )

    return check_conformance(
        required_output_type=script.output_type,
        provided_data=out_snap.data,
        obs=obs,
        policy=script.specification.policy,
        node_id=script.name,
        contract_id=str(script.contract_id),
    )
