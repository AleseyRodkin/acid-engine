from acid_engine.explain.explainer import explain_conformance
from acid_engine.level2.conformance import (
    ConformanceLevel,
    ConformanceResult,
    ConformanceStatus,
)
from acid_engine.level2.failure import FailureReason
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import lock_for_script, replay_run
from acid_engine.worker import live_toolchain


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
        version=Version(1, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=lambda x: x * 2,
        name="double",
    )
    iface, plan = lock_for_script(script)
    result = replay_run(
        plan,
        script,
        5,
        expected_output=10,
        iface=iface,
        toolchain=live_toolchain(),
    )
    assert result.ok
