from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.python_runtime import run_script


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

    # Execute through leaf
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