import pytest
from acid_engine.execution.history import (
    RunRecord, HistoryStore, replay_from_record, rollback_to,
)
from acid_engine.containers.observation import ExecutionObservation
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.scripts.specification import Specification
from acid_engine.scripts.module import ScriptModule


def test_history_store():
    store = HistoryStore()
    obs = ExecutionObservation.create(0, 0.001, "ok")
    record = RunRecord(
        run_id="r1", plan_hash="abc", timestamp=123.0,
        input_data=5, output_data=10, observation=obs, success=True,
    )
    store.add(record)
    assert store.last().run_id == "r1"
    assert rollback_to(store, "r1") is not None

def test_replay_from_record():
    script = ScriptModule(
        contract_id=ContractId("t", "x2"),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=lambda x: x * 2,
        name="double",
    )
    obs = ExecutionObservation.create(0, 0.001, "ok")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    assert replay_from_record(record, script, expected_output=10)