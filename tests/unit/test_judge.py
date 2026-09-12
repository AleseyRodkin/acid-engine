from __future__ import annotations

from pathlib import Path

from acid_engine.judge import RUNTIME_UNPINNED, judge_script, judge_script_from_lock
from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import lock_for_script
from acid_engine.worker import runtime_hashes, source_hash
from examples.bones.n_plus_one import build_script

ROOT = Path(__file__).resolve().parents[2]


def _tc() -> dict:
    return {"worker_hash": source_hash(), "runtime_hashes": runtime_hashes()}


def _script(impl, name="s"):
    return ScriptModule(
        contract_id=ContractId("t", name),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(max_latency_ms=200.0)),
        input_type="int",
        output_type="int",
        implementation=impl,
        name=name,
    )


def test_judge_without_plan_is_skipped():
    result = judge_script(build_script(), {"n": 3})
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert result.data is None
    assert result.observation is None
    assert "self-lock" in result.message.lower()


def test_judge_bones_with_plan_pass():
    script = build_script()
    iface, plan = lock_for_script(script)
    result = judge_script(script, {"n": 3}, plan=plan, iface=iface, toolchain=_tc())
    assert result.ok
    assert result.data == {"n": 4}


def test_judge_plan_without_toolchain_is_skipped():
    script = build_script()
    iface, plan = lock_for_script(script)
    result = judge_script(script, {"n": 3}, plan=plan, iface=iface)
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert result.data is None
    assert RUNTIME_UNPINNED in result.message


def test_judge_incomplete_toolchain_fails():
    script = build_script()
    iface, plan = lock_for_script(script)
    result = judge_script(
        script, {"n": 3}, plan=plan, iface=iface, toolchain={"worker_hash": source_hash()}
    )
    assert result.status == ConformanceStatus.FAIL
    assert not result.ok
    assert result.failure is not None
    assert result.failure.property_name == "runtime_hash"


def test_judge_script_from_lock_bones_pass():
    script = build_script()
    result = judge_script_from_lock(
        script, {"n": 3}, ROOT / "examples" / "bones" / "n_plus_one.plan.json"
    )
    assert result.ok
    assert result.data == {"n": 4}


def test_pipeline_without_plan_is_skipped():
    from acid_engine.level3.pipeline import Pipeline

    result = Pipeline(build_script()).execute({"n": 3})
    assert result.status == ConformanceStatus.SKIPPED
    assert result.data is None
    assert "self-lock" in result.message.lower()


def test_judge_swapped_body_fail_without_run():
    good = _script(lambda x: x + 1)
    called = []

    def swapped(x):
        called.append(x)
        return 0

    bad = _script(swapped)
    iface, plan = lock_for_script(good)
    result = judge_script(bad, 1, plan=plan, iface=iface, toolchain=_tc())
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert called == []


def test_judge_plan_without_iface_does_not_run():
    good = _script(lambda x: x + 1)
    called = []

    def swapped(x):
        called.append(x)
        return 0

    bad = _script(swapped)
    _iface, plan = lock_for_script(good)
    result = judge_script(bad, 1, plan=plan, iface=None)
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert called == []


def test_judge_missing_is_skipped():
    script = ScriptModule(
        contract_id=ContractId("t", "empty"),
        version=Version(1, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=None,
        name="empty",
    )
    iface, plan = lock_for_script(script)
    result = judge_script(script, 1, plan=plan, iface=iface, toolchain=_tc())
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
