import pytest
from acid_engine.scripts.specification import (
    Parameters, Policy, ImplementationRequirements, Specification,
)
from acid_engine.scripts.module import ScriptModule
from acid_engine.scripts.python_runtime import run_script
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.containers.port import PortRef
from acid_engine.containers.snapshot import ContainerSnapshot

def test_specification_serialization():
    params = Parameters({"threshold": 0.8})
    policy = Policy(pure=True, max_latency_ms=100)
    impl_req = ImplementationRequirements(
        required_methods=("transform",),
        required_exports=("version",),
    )
    spec = Specification(parameters=params, policy=policy, implementation_requirements=impl_req)
    d = spec.to_canonical_dict()
    assert d["parameters"]["values"] == {"threshold": 0.8}
    assert d["policy"]["pure"] == True
    assert d["implementation_requirements"]["required_methods"] == ["transform"]

def test_script_module_creation():
    script = ScriptModule(
        contract_id=ContractId("test", "add1"),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=lambda x: x + 1,
        name="increment",
    )
    assert script.contract_id.name == "add1"
    assert script.name == "increment"

def test_run_script_success():
    script = ScriptModule(
        contract_id=ContractId("test", "add1"),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=lambda x: x + 1,
        name="increment",
    )
    in_port = PortRef(module="test", direction="input", name="val")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=3,
    )
    out_snap, obs, delta, state = run_script(script, input_snap)
    assert out_snap.data == 4
    assert obs.status == "completed"
    assert delta.cardinality_delta == 0
    assert state.status == "completed"

def test_run_script_failure():
    def failing_impl(x):
        raise ValueError("bad")
    script = ScriptModule(
        contract_id=ContractId("test", "fail"),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=failing_impl,
        name="failer",
    )
    in_port = PortRef(module="test", direction="input", name="val")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=0,
    )
    out_snap, obs, delta, state = run_script(script, input_snap)
    assert out_snap.data is None
    assert obs.status == "failed"
    assert delta.status == "failed"
    assert state.status == "failed"
    assert "bad" in state.error_message