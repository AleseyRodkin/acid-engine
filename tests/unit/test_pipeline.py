from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.pipeline import Pipeline, PipelineResult
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import lock_for_script
from acid_engine.worker import runtime_hashes, source_hash


def _tc() -> dict:
    return {"worker_hash": source_hash(), "runtime_hashes": runtime_hashes()}


def _script(impl, name="increment"):
    return ScriptModule(
        contract_id=ContractId("test", "inc"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(max_latency_ms=100)),
        input_type="int",
        output_type="int",
        implementation=impl,
        name=name,
    )


def test_pipeline_with_script_module():
    script = _script(lambda x: x + 1)
    iface, plan = lock_for_script(script)
    pipeline = Pipeline(script, plan=plan, iface=iface, toolchain=_tc())
    result = pipeline.execute(5)
    assert isinstance(result, PipelineResult)
    assert result.ok, f"Expected PASS, got {result.message}"
    assert result.data == 6
    assert result.observation is not None
    assert result.observation.status == "completed"


def test_pipeline_interface_never_pass():
    iface = InterfaceContract(
        contract_id=ContractId("test", "iface"),
        version=Version(1, 0, 0),
        inputs={"x": "int"},
        outputs={"y": "int"},
        constraints={},
    )
    result = Pipeline(iface).execute("garbage")
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert result.data is None
    assert result.observation is None
    assert "not executed" in result.message.lower()


def test_pipeline_rejects_swapped_body_against_plan():
    good = _script(lambda x: x + 1)
    called = []

    def swapped(x):
        called.append(x)
        return x + 100

    bad = _script(swapped)
    iface, plan = lock_for_script(good)
    result = Pipeline(bad, plan=plan, iface=iface, toolchain=_tc()).execute(1)
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "module_hash"
    assert called == []
    assert result.data is None
