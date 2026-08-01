import pytest
from acid_engine.explain.explainer import explain_conformance
from acid_engine.contracts.conformance import (
    ConformanceResult, ConformanceStatus, ConformanceLevel,
)
from acid_engine.contracts.failure import FailureReason
from acid_engine.execution.runner import replay_run
from acid_engine.execution.plan_lock import PlanLock
from acid_engine.execution.modes import ExecutionMode
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.scripts.specification import Specification
from acid_engine.scripts.module import ScriptModule


def test_explain_pass():
    result = ConformanceResult(
        status=ConformanceStatus.PASS,
        level=ConformanceLevel.OPERATIONAL,
        message="ok",
    )
    assert "[PASS]" in explain_conformance(result)

def test_explain_fail():
    failure = FailureReason(
        node_id="n1",
        contract_id="c1",
        property_name="p",
        expected=1,
        actual=2,
    )
    result = ConformanceResult(
        status=ConformanceStatus.FAIL,
        level=ConformanceLevel.STRUCTURAL,
        message="bad",
        failure=failure,
    )
    explanation = explain_conformance(result)
    assert "expected=1" in explanation
    assert "actual=2" in explanation

def test_replay_ok():
    script = ScriptModule(
        contract_id=ContractId("t", "x2"),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=lambda x: x * 2,
        name="double",
    )
    plan = PlanLock.create(
        plan_id="replay-test",
        interface_contract_hash="hash",
        resolved_policies={},
        module_hashes={},
        execution_mode=ExecutionMode.LIGHT,
    )
    assert replay_run(plan, script, 5, expected_output=10)