from pathlib import Path

from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import (
    bind_script_to_plan,
    dump_script_lock,
    execute_plan,
    lock_for_script,
    replay_run,
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


def _iface(script: ScriptModule) -> InterfaceContract:
    return InterfaceContract(
        contract_id=ContractId("t", "iface"),
        version=Version(1, 0, 0),
        inputs={"x": "int"},
        outputs={"y": "int"},
        constraints={},
        module_hashes={script.name: script.content_hash},
    )


def _plan(iface: InterfaceContract, script: ScriptModule) -> PlanLock:
    return PlanLock.create(
        plan_id="p1",
        interface_contract_hash=iface.content_hash,
        resolved_policies={},
        module_hashes={script.name: script.content_hash},
        execution_mode=ExecutionMode.NORMAL,
    )


def test_execute_plan_without_toolchain_is_skipped():
    script = _script(lambda x: x * 2)
    iface = _iface(script)
    plan = _plan(iface, script)
    result = execute_plan(iface, plan, script, 5)
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert result.data is None
    assert "runtime not pinned" in result.message


def test_execute_plan_ok_when_hash_matches():
    script = _script(lambda x: x * 2)
    iface = _iface(script)
    plan = _plan(iface, script)
    result = execute_plan(iface, plan, script, 5, toolchain=live_toolchain())
    assert result.ok
    assert result.data == 10
    assert result.observation is not None
    assert bind_script_to_plan(plan, script) is None


def test_execute_plan_fails_on_swapped_body_and_does_not_run():
    good = _script(lambda x: x * 2)
    called = []

    def swapped(x):
        called.append(x)
        return x * 100

    bad = _script(swapped)
    iface = _iface(good)
    plan = _plan(iface, good)
    result = execute_plan(iface, plan, bad, 5, toolchain=live_toolchain())
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "module_hash"
    assert called == []


def test_execute_plan_skipped_without_hashes():
    script = _script(lambda x: x)
    iface = _iface(script)
    plan = PlanLock.create(
        plan_id="empty",
        interface_contract_hash=iface.content_hash,
        resolved_policies={},
        module_hashes={},
        execution_mode=ExecutionMode.NORMAL,
    )
    result = execute_plan(iface, plan, script, 1, toolchain=live_toolchain())
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert result.data is None


def test_execute_plan_fails_on_interface_mismatch():
    script = _script(lambda x: x + 1)
    iface = _iface(script)
    other = InterfaceContract(
        contract_id=ContractId("t", "other"),
        version=Version(1, 0, 0),
        inputs={"x": "int"},
        outputs={"y": "int"},
        constraints={"x": 1},
    )
    plan = PlanLock.create(
        plan_id="p",
        interface_contract_hash=other.content_hash,
        resolved_policies={},
        module_hashes={script.name: script.content_hash},
        execution_mode=ExecutionMode.NORMAL,
    )
    result = execute_plan(iface, plan, script, 1, toolchain=live_toolchain())
    assert not result.ok
    assert result.failure.property_name == "interface_contract_hash"


def test_bind_wrong_key_is_skipped_not_fallback():
    script = _script(lambda x: x + 1, name="scale")
    iface = InterfaceContract(
        contract_id=ContractId("t", "iface"),
        version=Version(1, 0, 0),
        inputs={"x": "int"},
        outputs={"y": "int"},
        constraints={},
        module_hashes={"unrelated": script.content_hash},
    )
    plan = PlanLock.create(
        plan_id="p",
        interface_contract_hash=iface.content_hash,
        resolved_policies={},
        module_hashes={"unrelated": script.content_hash},
        execution_mode=ExecutionMode.NORMAL,
    )
    result = execute_plan(iface, plan, script, 1, toolchain=live_toolchain())
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok


def test_replay_requires_lock_hash():
    script = _script(lambda x: x * 2)
    iface, plan = lock_for_script(script)
    tc = live_toolchain()
    assert replay_run(
        plan, script, 5, expected_output=10, iface=iface, toolchain=tc
    ).ok

    bad = _script(lambda x: x * 100)
    mismatch = replay_run(
        plan, bad, 5, expected_output=10, iface=iface, toolchain=tc
    )
    assert not mismatch.ok
    assert mismatch.status == ConformanceStatus.FAIL


def test_replay_without_expected_is_skipped():
    called = []

    def body(x):
        called.append(x)
        return x * 2

    script = _script(body)
    iface, plan = lock_for_script(script)
    result = replay_run(
        plan, script, 5, iface=iface, toolchain=live_toolchain()
    )
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert called == []


def test_replay_without_iface_is_skipped_and_does_not_run():
    called = []

    def body(x):
        called.append(x)
        return x * 2

    script = _script(body)
    _iface, plan = lock_for_script(script)
    result = replay_run(
        plan, script, 5, expected_output=10, toolchain=live_toolchain()
    )
    assert result.status == ConformanceStatus.SKIPPED
    assert "iface" in result.message
    assert called == []


def test_replay_without_toolchain_is_skipped_and_does_not_run():
    called = []

    def body(x):
        called.append(x)
        return x * 2

    script = _script(body)
    iface, plan = lock_for_script(script)
    result = replay_run(plan, script, 5, expected_output=10, iface=iface)
    assert result.status == ConformanceStatus.SKIPPED
    assert "runtime not pinned" in result.message
    assert called == []


def test_replay_output_mismatch_is_fail():
    script = _script(lambda x: x * 2)
    iface, plan = lock_for_script(script)
    result = replay_run(
        plan,
        script,
        5,
        expected_output=999,
        iface=iface,
        toolchain=live_toolchain(),
    )
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "output"


def test_replay_poisoned_runtime_does_not_execute():
    called = []

    def body(x):
        called.append(x)
        return x * 2

    script = _script(body)
    iface, plan = lock_for_script(script)
    payload = dump_script_lock(script)
    tool = dict(payload["toolchain"])
    hashes = dict(tool["runtime_hashes"])
    hashes["acid_engine/level3/script/runner.py"] = "0" * 64
    tool["runtime_hashes"] = hashes
    poisoned = dict(payload)
    poisoned["toolchain"] = tool
    result = replay_run(
        plan, script, 5, expected_output=10, iface=iface, toolchain=poisoned
    )
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure is not None
    assert result.failure.property_name == "runtime_hash"
    assert called == []


def test_replay_modified_dependency_does_not_execute(tmp_path: Path) -> None:
    from acid_engine.cli import load_script_from_file

    helper = tmp_path / "helper.py"
    helper.write_text("def process(x):\n    return x * 2\n", encoding="utf-8")
    entry = tmp_path / "entry.py"
    entry.write_text(
        """
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def entry(data):
    from helper import process
    return process(data)


script = ScriptModule(
    contract_id=ContractId("t", "entry"),
    version=Version(0, 1, 0),
    specification=Specification(policy=Policy()),
    input_type="int",
    output_type="int",
    implementation=entry,
    name="entry",
)
""",
        encoding="utf-8",
    )
    script = load_script_from_file(entry)
    iface, plan = lock_for_script(script)
    payload = dump_script_lock(script)
    honest = replay_run(
        plan, script, 5, expected_output=10, iface=iface, toolchain=payload
    )
    assert honest.ok, honest.message
    helper.write_text("def process(x):\n    return 4995\n", encoding="utf-8")
    result = replay_run(
        plan, script, 5, expected_output=10, iface=iface, toolchain=payload
    )
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure is not None
    assert result.failure.property_name == "dependency_hash"
    assert result.failure.actual != "4995"
