import pytest
from acid_engine.level2.conformance import (
    check_conformance,
    ConformanceStatus,
    ConformanceLevel,
)
from acid_engine.level2.failure import FailureReason
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level2.specification import Policy


def test_pass_int():
    obs = ExecutionObservation.create(0, 0.001, "completed", input_hash="a", output_hash="b")
    policy = Policy(max_latency_ms=10)
    result = check_conformance("int", 42, obs, policy, node_id="n", contract_id="c")
    assert result.ok

def test_type_mismatch():
    obs = ExecutionObservation.create(0, 0.001, "completed")
    policy = Policy()
    result = check_conformance("int", "string", obs, policy)
    assert not result.ok
    assert result.failure.property_name == "output_type"

def test_latency_violation():
    obs = ExecutionObservation.create(0, 0.1, "completed", input_hash="a", output_hash="b")  # 100ms
    policy = Policy(max_latency_ms=50)
    result = check_conformance("int", 1, obs, policy)
    assert not result.ok
    assert "Latency" in result.message