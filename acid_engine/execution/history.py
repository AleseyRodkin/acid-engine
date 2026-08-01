"""История запусков: запись, replay, rollback."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import uuid
from acid_engine.execution.plan_lock import PlanLock
from acid_engine.execution.modes import ExecutionMode
from acid_engine.containers.observation import ExecutionObservation
from acid_engine.contracts.serialization import content_hash_of


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
    """Простое in-memory хранилище истории (в будущем — БД)."""
    records: List[RunRecord] = field(default_factory=list)

    def add(self, record: RunRecord):
        self.records.append(record)

    def last(self) -> Optional[RunRecord]:
        return self.records[-1] if self.records else None

    def find_by_plan(self, plan_hash: str) -> List[RunRecord]:
        return [r for r in self.records if r.plan_hash == plan_hash]


def replay_from_record(
    record: RunRecord,
    script,
    expected_output: Optional[Any] = None,
) -> bool:
    """
    Переигрывает выполнение по исторической записи.
    Возвращает True, если результат совпадает.
    """
    from acid_engine.scripts.python_runtime import run_script
    from acid_engine.containers.port import PortRef
    from acid_engine.containers.snapshot import ContainerSnapshot

    in_port = PortRef(module=script.contract_id.name, direction="input", name="value")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=record.input_data,
    )
    out_snap, obs, _, _ = run_script(script, input_snap)
    if expected_output is not None:
        return out_snap.data == expected_output
    return out_snap.data == record.output_data


def rollback_to(history: HistoryStore, run_id: str) -> Optional[RunRecord]:
    """Возвращает запись с указанным run_id (имитация отката)."""
    for r in reversed(history.records):
        if r.run_id == run_id:
            return r
    return None