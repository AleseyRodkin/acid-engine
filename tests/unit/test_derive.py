import pytest
from acid_engine.derive.operations import derive_map, derive_filter
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.scripts.specification import Specification
from acid_engine.scripts.module import ScriptModule
from acid_engine.scripts.python_runtime import run_script
from acid_engine.containers.port import PortRef
from acid_engine.containers.snapshot import ContainerSnapshot


def test_derive_map():
    src = ScriptModule(
        contract_id=ContractId("test", "nums"),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="list",
        output_type="list",
        implementation=lambda x: x,
        name="identity",
    )
    mapped = derive_map(src, lambda x: x * 2)
    in_port = PortRef("test", "input", "val")
    snap = ContainerSnapshot.create(in_port, src.contract_id, src.content_hash, [1,2,3])
    out, _, _, _ = run_script(mapped, snap)
    assert out.data == [2,4,6]

def test_derive_filter():
    src = ScriptModule(
        contract_id=ContractId("test", "nums"),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="list",
        output_type="list",
        implementation=lambda x: x,
    )
    filtered = derive_filter(src, lambda x: x > 0)
    snap = ContainerSnapshot.create(
        PortRef("test","in","v"), src.contract_id, src.content_hash, [-1,0,3,5]
    )
    out, _, _, _ = run_script(filtered, snap)
    assert out.data == [3,5]