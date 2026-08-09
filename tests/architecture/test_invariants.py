import pytest
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.port import PortRef
from acid_engine.level2.identity import ContractId
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.script.modes import ExecutionMode


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