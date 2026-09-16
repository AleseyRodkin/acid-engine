from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import lock_for_script
from acid_engine.level4.history import (
    HistoryStore,
    RunRecord,
    find_record,
    replay_from_record,
)
from acid_engine.worker import live_toolchain


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


def _replay(record, script, plan, iface, **kwargs):
    return replay_from_record(
        record,
        script,
        plan=plan,
        iface=iface,
        toolchain=live_toolchain(),
        **kwargs,
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
    iface, plan = lock_for_script(script)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    result = _replay(record, script, plan, iface)
    assert result.ok
    assert result.status == ConformanceStatus.PASS


def test_replay_from_record_uses_record_output_as_fact():
    script = _script(lambda x: x * 2)
    iface, plan = lock_for_script(script)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    assert _replay(record, script, plan, iface).ok


def test_replay_from_record_mismatch_is_fail():
    script = _script(lambda x: x * 2)
    iface, plan = lock_for_script(script)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 999, obs, True)
    result = _replay(record, script, plan, iface)
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "output"


def test_replay_from_record_explicit_expected():
    script = _script(lambda x: x * 2)
    iface, plan = lock_for_script(script)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    assert _replay(record, script, plan, iface, expected_output=10).ok
    bad = _replay(record, script, plan, iface, expected_output=999)
    assert not bad.ok
    assert bad.status == ConformanceStatus.FAIL


def test_replay_from_record_without_plan_is_skipped():
    script = _script(lambda x: x * 2)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    result = replay_from_record(record, script)
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok


def test_replay_from_record_without_iface_is_skipped():
    script = _script(lambda x: x * 2)
    _iface, plan = lock_for_script(script)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    result = replay_from_record(
        record, script, plan=plan, toolchain=live_toolchain()
    )
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok


def test_replay_swapped_body_fails_against_record():
    good = _script(lambda x: x * 2)
    called = []

    def swapped(x):
        called.append(x)
        return x * 100

    bad = _script(swapped)
    iface, plan = lock_for_script(good)
    obs = ExecutionObservation.create(0, 0.001, "completed")
    record = RunRecord("r1", "hash", 0.0, 5, 10, obs, True)
    assert _replay(record, good, plan, iface).ok
    result = _replay(record, bad, plan, iface)
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert called == []
