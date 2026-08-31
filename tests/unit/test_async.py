import asyncio

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.module.composite import CompositeModule
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.script.async_module import AsyncScriptModule
from acid_engine.level3.script.async_runtime import run_async_script


def test_async_script():
    async def async_inc(x):
        return x + 1

    script = AsyncScriptModule(
        contract_id=ContractId("test", "async_inc"),
        version=Version(1, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=async_inc,
        name="async_inc",
    )
    in_port = PortRef(module="test", direction="input", name="val")
    input_snap = ContainerSnapshot.create(in_port, script.contract_id, script.content_hash, 5)

    async def _run():
        return await run_async_script(script, input_snap)

    out_snap, obs, delta, state = asyncio.run(_run())
    assert out_snap.data == 6
    assert obs.status == "completed"


def test_composite_with_async_leaf():
    async def async_double(x):
        return x * 2

    script = AsyncScriptModule(
        contract_id=ContractId("test", "async_double"),
        version=Version(1, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=async_double,
        name="double",
    )
    leaf = LeafModule(module_id="leaf", script=script)
    g = DependencyGraph()
    g.add_node("leaf", payload=leaf)
    composite = CompositeModule(
        module_id="comp",
        graph=g,
        modules={"leaf": leaf},
        contract_id=ContractId("test", "comp"),
        version=Version(1, 0, 0),
        input_node="leaf",
        output_node="leaf",
    )
    result = composite.execute(10)
    assert result.data == 20
