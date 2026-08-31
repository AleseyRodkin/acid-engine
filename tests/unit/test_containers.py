import pytest
from acid_engine.level2.identity import ContractId
from acid_engine.level3.container.delta import ContainerDelta
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.state import ExecutionState, ExecutionStatus


def test_port_ref():
    p = PortRef("mod", "input", "val")
    assert str(p) == "mod.input.val"
    p2 = PortRef.parse("mod.input.val")
    assert p == p2

def test_snapshot_immutable():
    snap = ContainerSnapshot.create(
        port_ref=PortRef("m", "in", "x"),
        contract_id=ContractId("ns", "name"),
        contract_hash="abc",
        data=42,
    )
    with pytest.raises(Exception):
        snap.data = 43  # dataclass frozen

def test_snapshot_hash_deterministic():
    s1 = ContainerSnapshot.create(PortRef("m","in","x"), ContractId("ns","n"), "abc", [1,2])
    s2 = ContainerSnapshot.create(PortRef("m","in","x"), ContractId("ns","n"), "abc", [1,2])
    assert s1.content_hash == s2.content_hash
    s3 = ContainerSnapshot.create(PortRef("m","in","x"), ContractId("ns","n"), "abc", [2,1])
    assert s1.content_hash != s3.content_hash

def test_state_transitions():
    st = ExecutionState()
    assert st.status == ExecutionStatus.PENDING
    st.mark_running()
    assert st.status == ExecutionStatus.RUNNING
    st.mark_completed()
    assert st.status == ExecutionStatus.COMPLETED
    st.mark_failed("err")
    assert st.status == ExecutionStatus.FAILED
    assert st.error_message == "err"

def test_observation_creation():
    obs = ExecutionObservation.create(1.0, 2.0, "ok", effects=("write",), input_hash="ih", output_hash="oh")
    assert obs.latency_ms == 1000.0
    assert obs.effects_observed == ("write",)

def test_delta():
    d = ContainerDelta(input_cardinality=1, output_cardinality=2, input_hash="a", output_hash="b", status="ok", latency_ms=5.0)
    assert d.cardinality_delta == 1