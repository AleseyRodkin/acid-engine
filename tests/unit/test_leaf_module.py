import pytest
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.scripts.specification import Specification
from acid_engine.scripts.module import ScriptModule
from acid_engine.modules.leaf import LeafModule
from acid_engine.containers.port import PortRef
from acid_engine.containers.snapshot import ContainerSnapshot
from acid_engine.scripts.python_runtime import run_script


def test_leaf_module_delegation():
    script = ScriptModule(
        contract_id=ContractId("test", "x2"),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=lambda x: x * 2,
        name="doubler",
    )
    leaf = LeafModule(module_id="leaf1", script=script)

    # Выполнение через leaf
    in_port = PortRef(module=script.contract_id.name, direction="input", name="val")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=5,
    )
    out_snap, obs, delta, state = run_script(leaf.script, input_snap)
    assert out_snap.data == 10
    assert leaf.contract_id == script.contract_id
    assert leaf.content_hash == script.content_hash