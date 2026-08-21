import pytest
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.port import PortRef
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.module.leaf import LeafModule


def test_container_snapshot_immutable():
    snap = ContainerSnapshot.create(
        port_ref=PortRef("m", "in", "x"),
        contract_id=ContractId("ns", "n"),
        contract_hash="abc",
        data=42,
    )
    with pytest.raises(Exception):
        snap.data = 43


def test_plan_lock_frozen():
    plan = PlanLock.create(
        plan_id="p1",
        interface_contract_hash="h",
        resolved_policies={},
        module_hashes={},
        execution_mode=ExecutionMode.NORMAL,
    )
    with pytest.raises(Exception):
        plan.execution_mode = ExecutionMode.LIGHT


def test_plan_lock_tracks_implementation_body():
    """Подмена тела при той же декларации меняет module hash в plan.lock."""

    def plus_one(x):
        return x + 1

    def plus_hundred(x):
        return x + 100

    def leaf_for(impl):
        script = ScriptModule(
            contract_id=ContractId("demo", "x_plus"),
            version=Version(0, 1, 0),
            specification=Specification(),
            input_type="int",
            output_type="int",
            implementation=impl,
            name="x_plus",
        )
        return LeafModule(module_id="leaf", script=script)

    a = leaf_for(plus_one)
    b = leaf_for(plus_hundred)
    assert a.content_hash != b.content_hash

    plan_a = PlanLock.create(
        plan_id="p",
        interface_contract_hash="iface",
        resolved_policies={},
        module_hashes={a.module_id: a.content_hash},
        execution_mode=ExecutionMode.NORMAL,
    )
    plan_b = PlanLock.create(
        plan_id="p",
        interface_contract_hash="iface",
        resolved_policies={},
        module_hashes={b.module_id: b.content_hash},
        execution_mode=ExecutionMode.NORMAL,
    )
    assert plan_a.content_hash != plan_b.content_hash


def test_stub_never_pass():
    from acid_engine.level3.pipeline import Pipeline
    from acid_engine.level3.interface.contract import InterfaceContract
    from acid_engine.level3.orchestration.adapter import LocalAdapter
    from acid_engine.level2.conformance import ConformanceStatus

    iface = InterfaceContract(
        contract_id=ContractId("test", "iface"),
        version=Version(1, 0, 0),
        inputs={},
        outputs={},
        constraints={},
    )
    pipe_result = Pipeline(iface).execute({"anything": 1})
    assert pipe_result.status != ConformanceStatus.PASS
    assert not pipe_result.ok

    adapter = LocalAdapter()
    plan = PlanLock.create(
        plan_id="p",
        interface_contract_hash="h",
        resolved_policies={},
        module_hashes={},
        execution_mode=ExecutionMode.NORMAL,
    )
    adapter_result = adapter.get_result(adapter.submit_plan(plan))
    assert adapter_result is not None
    assert adapter_result.status != ConformanceStatus.PASS
    assert not adapter_result.ok


def test_bool_not_int():
    from acid_engine.level2.conformance import check_conformance, ConformanceStatus
    from acid_engine.level3.container.observation import ExecutionObservation
    from acid_engine.level2.specification import Policy
    obs = ExecutionObservation.create(0, 0.001, "completed")
    result = check_conformance("int", True, obs, Policy())
    assert result.status == ConformanceStatus.FAIL
    assert not result.ok


def test_observation_no_stdout_by_default():
    import io, contextlib
    from acid_engine.level3.container.observation import ExecutionObservation
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ExecutionObservation.create(0, 0.001, "completed")
    assert buf.getvalue() == ""
