from acid_engine.level4.history import (
    RunRecord,
    HistoryStore,
    replay_from_record,
    find_record,
)
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level3.script.module import ScriptModule


def _script(impl, name="double"):
    return ScriptModule(
        contract_id=ContractId("t", name),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(max_latency_ms=200)),
        input_type="int",
        output_type="int",
        implementation=impl,
        name=name,
    )


def test_history_store_and_find():
    store = HistoryStore()
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord(
        run_id="r1",
        plan_hash="abc",
        timestamp=123.0,
        input_data=5,
        output_data=10,
        observation=obs,
        success=True,
    )
    store.add(record)
    assert store.last().run_id == "r1"
    assert find_record(store, "r1") is record
    assert find_record(store, "missing") is None


def test_replay_from_record_ok():
    script = _script(lambda x: x * 2)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    result = replay_from_record(record, script)
    assert result.ok
    assert result.status == ConformanceStatus.PASS


def test_replay_from_record_uses_record_output_as_fact():
    script = _script(lambda x: x * 2)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    # record claims 10; script would produce 10 — pass
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    assert replay_from_record(record, script).ok


def test_replay_from_record_mismatch_is_fail():
    script = _script(lambda x: x * 2)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    # history claims 999, script produces 10
    record = RunRecord("r1", "hash", 0.0, 5, 999, obs, True)
    result = replay_from_record(record, script)
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "output"


def test_replay_from_record_explicit_expected():
    script = _script(lambda x: x * 2)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    assert replay_from_record(record, script, expected_output=10).ok
    bad = replay_from_record(record, script, expected_output=999)
    assert not bad.ok
    assert bad.status == ConformanceStatus.FAIL


def test_replay_swapped_body_fails_against_record():
    good = _script(lambda x: x * 2)
    bad = _script(lambda x: x * 100)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    assert replay_from_record(record, good).ok
    swapped = replay_from_record(record, bad)
    assert not swapped.ok
    assert swapped.failure.actual == 500
