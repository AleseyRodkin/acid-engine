import os
import tempfile

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.artifact import ArtifactRef, artifact_ref_from_callable
from acid_engine.level3.script.runner import execute_plan
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.script.modes import ExecutionMode


BODY = '''def plus_one(x):
    return x + 1
'''


def _iface_plan(script):
    iface = InterfaceContract(
        contract_id=ContractId("t", "iface"),
        version=Version(1, 0, 0),
        inputs={"x": "int"},
        outputs={"y": "int"},
        constraints={},
        module_hashes={script.name: script.content_hash},
    )
    plan = PlanLock.create(
        plan_id="p",
        interface_contract_hash=iface.content_hash,
        resolved_policies={},
        module_hashes={script.name: script.content_hash},
        execution_mode=ExecutionMode.NORMAL,
    )
    return iface, plan


def _script(**kwargs):
    kw = dict(
        contract_id=ContractId("t", "s"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(max_latency_ms=500)),
        input_type="int",
        output_type="int",
        name="s",
    )
    kw.update(kwargs)
    return ScriptModule(**kw)


def test_resolve_python_file_and_run():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "plus.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(BODY)
        # body_hash empty: 2b allows run without hash check
        art = ArtifactRef(
            language="python",
            file=path,
            entry="plus_one",
            canon="ast",
            body_hash="",
        )
        script = _script(implementation=None, artifact=art)
        iface, plan = _iface_plan(script)
        result = execute_plan(iface, plan, script, 3)
        assert result.ok
        assert result.data == 4


def test_unknown_language_is_fail_not_eval():
    art = ArtifactRef(
        language="javascript",
        file="x.js",
        entry="fn",
        canon="opaque",
        body_hash="",
    )
    script = _script(implementation=None, artifact=art)
    iface, plan = _iface_plan(script)
    result = execute_plan(iface, plan, script, 1)
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "language"
    assert result.data is None


def test_broken_file_is_fail():
    art = ArtifactRef(
        language="python",
        file="/tmp/acid_missing_artifact_nope.py",
        entry="plus_one",
        canon="ast",
        body_hash="",
    )
    script = _script(implementation=None, artifact=art)
    iface, plan = _iface_plan(script)
    result = execute_plan(iface, plan, script, 1)
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "artifact"


def test_missing_impl_and_artifact_is_skipped():
    script = _script(implementation=None, artifact=None)
    iface, plan = _iface_plan(script)
    result = execute_plan(iface, plan, script, 1)
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert result.data is None


def test_callable_still_preferred_over_artifact():
    def plus_one(x):
        return x + 1

    art = ArtifactRef(
        language="javascript",
        file="nope.js",
        entry="x",
        canon="opaque",
        body_hash="",
    )
    script = _script(implementation=plus_one, artifact=art)
    iface, plan = _iface_plan(script)
    result = execute_plan(iface, plan, script, 2)
    assert result.ok
    assert result.data == 3
