"""toolchain sits next to the lock, not in identity."""
from __future__ import annotations

import sys

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import dump_script_lock, load_script_lock, lock_for_script


def _script():
    return ScriptModule(
        contract_id=ContractId("t", "inc"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(max_latency_ms=200.0)),
        input_type="int",
        output_type="int",
        implementation=lambda x: x + 1,
        name="inc",
    )


def test_dump_includes_toolchain_outside_identity():
    script = _script()
    payload = dump_script_lock(script)
    tool = payload["toolchain"]
    assert tool["python_version"] == f"{sys.version_info.major}.{sys.version_info.minor}"
    assert tool["canon_kind"] in {"ast", "bytecode", "opaque", "partial"}
    from acid_engine.worker import source_hash

    assert tool["worker_hash"] == source_hash()
    assert len(tool["worker_hash"]) == 64
    iface, plan = lock_for_script(script)
    assert payload["module_hashes"] == dict(plan.module_hashes)
    assert payload["interface_contract_hash"] == plan.interface_contract_hash
    assert "toolchain" not in plan.to_canonical_dict()
    assert "python_version" not in script._identity_dict()


def test_load_ignores_toolchain_and_still_binds():
    script = _script()
    payload = dump_script_lock(script)
    iface, plan = load_script_lock(payload)
    assert plan.module_hashes[script.name] == script.content_hash
    without = dict(payload)
    without.pop("toolchain")
    iface2, plan2 = load_script_lock(without)
    assert plan2.module_hashes == plan.module_hashes
    assert iface2.content_hash == iface.content_hash


def test_public_exports_are_the_gate():
    import acid_engine

    assert acid_engine.__all__ == [
        "__version__",
        "judge_script",
        "dump_script_lock",
        "lock_for_script",
    ]
    assert "Pipeline" not in acid_engine.__all__
    assert acid_engine.__version__ == "0.2.0"
