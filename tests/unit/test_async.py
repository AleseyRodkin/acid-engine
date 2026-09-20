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
from acid_engine.level3.script.runner import lock_for_script
from acid_engine.worker import live_toolchain


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
    iface, plan = lock_for_script(script)
    result = composite.execute(10, plan=plan, iface=iface, toolchain=live_toolchain())
    assert result.data == 20


def test_composite_async_helper_swap_after_prepare_is_not_new_bytes(tmp_path):
    """Seal in _prepare_execution; disk swap after bind is not the run body."""
    from acid_engine.level2.local_deps import _SEALED, collect_local_dep_hashes
    from acid_engine.level3.script.runner import (
        _prepare_execution,
        dump_script_lock,
        load_script_lock,
    )

    helper = tmp_path / "helper.py"
    helper.write_text("def process(x):\n    return x * 2\n", encoding="utf-8")
    entry = tmp_path / "async_entry.py"
    entry.write_text(
        """
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level3.script.async_module import AsyncScriptModule
from helper import process

async def entry(x):
    return process(x)

script = AsyncScriptModule(
    contract_id=ContractId("t", "async_entry"),
    version=Version(0, 1, 0),
    specification=Specification(),
    input_type="int",
    output_type="int",
    implementation=entry,
    name="async_entry",
)
""",
        encoding="utf-8",
    )
    import importlib.util
    import sys

    _SEALED.set(None)
    sys.modules.pop("helper", None)
    sys.path.insert(0, str(tmp_path))
    spec = importlib.util.spec_from_file_location("async_entry", entry)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    script = mod.script
    assert collect_local_dep_hashes(script.implementation)
    payload = dump_script_lock(script)
    iface, plan = load_script_lock(payload)
    verified, blocked = _prepare_execution(
        iface, plan, script, toolchain=payload
    )
    assert blocked is None
    assert verified is not None
    helper.write_text("def process(x):\n    return 'SWAPPED'\n", encoding="utf-8")
    in_port = PortRef(module="t", direction="input", name="val")
    input_snap = ContainerSnapshot.create(
        in_port, script.contract_id, script.content_hash, 10
    )

    async def _run():
        return await run_async_script(script, input_snap, fn=verified.fn)

    out_snap, obs, _delta, _state = asyncio.run(_run())
    assert obs.status == "completed", obs.trace
    assert out_snap.data != "SWAPPED"
    assert out_snap.data == 20
