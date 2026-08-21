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
