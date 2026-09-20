"""toolchain sits next to the lock, not in identity."""
from __future__ import annotations

import sys

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.implementation_canon import canon_id_for
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import dump_script_lock, load_script_lock, lock_for_script
from acid_engine.worker import RUNTIME_PIN_PATHS, runtime_hashes, source_hash


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
    assert tool["canon"] == canon_id_for(tool["canon_kind"])
    assert tool["canon"].startswith("python.")
    assert tool["canon"].endswith(".v1")
    assert "canon" not in script._identity_dict()
    assert tool["worker_hash"] == source_hash()
    assert len(tool["worker_hash"]) == 64
    live_rt = runtime_hashes()
    assert tool["runtime_hashes"] == live_rt
    assert set(tool["runtime_hashes"]) == set(RUNTIME_PIN_PATHS)
    assert len(RUNTIME_PIN_PATHS) == 8
    assert "acid_engine/cli_judge.py" in RUNTIME_PIN_PATHS
    assert "acid_engine/action_driver.py" in RUNTIME_PIN_PATHS
    assert "acid_engine/cli.py" not in RUNTIME_PIN_PATHS
    assert "acid_engine/cli.py" not in tool["runtime_hashes"]
    assert "acid_engine/cli_judge.py" in tool["runtime_hashes"]
    assert payload.get("source_hash")
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


def test_crooked_plan_content_hash_is_load_error():
    script = _script()
    payload = dump_script_lock(script)
    payload["plan_content_hash"] = "0" * 64
    try:
        load_script_lock(payload)
        assert False, "expected plan_content_hash mismatch"
    except ValueError as e:
        assert "plan_content_hash mismatch" in str(e)
    payload.pop("plan_content_hash")
    iface, plan = load_script_lock(payload)
    assert plan.module_hashes[script.name] == script.content_hash


def test_public_exports_are_the_gate():
    import acid_engine

    assert acid_engine.__all__ == [
        "__version__",
        "judge_script",
        "judge_script_from_lock",
        "dump_script_lock",
        "lock_for_script",
        "build_receipt",
    ]
    assert "Pipeline" not in acid_engine.__all__
    assert acid_engine.__version__ == "0.2.33"


def test_verify_runtime_pin_ok_and_mismatch():
    from acid_engine.level2.conformance import ConformanceStatus
    from acid_engine.worker import verify_runtime_pin

    payload = dump_script_lock(_script())
    assert verify_runtime_pin(payload) is None
    bad = dict(payload)
    tool = dict(payload["toolchain"])
    hashes = dict(tool["runtime_hashes"])
    hashes["acid_engine/level2/implementation_canon.py"] = "0" * 64
    tool["runtime_hashes"] = hashes
    bad["toolchain"] = tool
    pin = verify_runtime_pin(bad)
    assert pin is not None
    assert pin.status == ConformanceStatus.FAIL
    assert pin.failure is not None
    assert pin.failure.property_name == "runtime_hash"
    missing = verify_runtime_pin({"plan_id": "x"})
    assert missing is not None
    assert missing.failure is not None
    assert missing.failure.property_name == "worker_hash"
    wrong_py = dict(payload)
    tool2 = dict(payload["toolchain"])
    tool2["python_version"] = "3.7"
    wrong_py["toolchain"] = tool2
    pin_py = verify_runtime_pin(wrong_py)
    assert pin_py is not None
    assert pin_py.failure is not None
    assert pin_py.failure.property_name == "python_version"
    assert "re-take the lock" in pin_py.message
    pin_kind = verify_runtime_pin(payload, live_canon_kind="bytecode")
    assert pin_kind is not None
    assert pin_kind.failure is not None
    assert pin_kind.failure.property_name == "canon_kind"


def test_cli_py_hash_is_not_a_runtime_pin():
    from acid_engine.level2.conformance import ConformanceStatus
    from acid_engine.worker import verify_runtime_pin

    payload = dump_script_lock(_script())
    tool = dict(payload["toolchain"])
    hashes = dict(tool["runtime_hashes"])
    hashes["acid_engine/cli.py"] = "0" * 64
    tool["runtime_hashes"] = hashes
    extra = dict(payload)
    extra["toolchain"] = tool
    assert verify_runtime_pin(extra) is None
    hashes["acid_engine/level2/implementation_canon.py"] = "0" * 64
    tool["runtime_hashes"] = hashes
    extra["toolchain"] = tool
    pin = verify_runtime_pin(extra)
    assert pin is not None
    assert pin.status == ConformanceStatus.FAIL
    assert pin.failure is not None
    assert pin.failure.property_name == "runtime_hash"


def test_research_shims_keep_import_path():
    from acid_engine.level0.live_code import LiveCodeView
    from acid_engine.level4.registry import ContractRegistry
    from acid_engine.services.logging.logger import ExecutionLogger

    assert LiveCodeView is not None
    assert ContractRegistry is not None
    assert ExecutionLogger is not None


def test_worker_source_does_not_import_cli():
    from pathlib import Path

    import acid_engine.worker as worker

    src = Path(worker.__file__).read_text(encoding="utf-8")
    assert "from acid_engine.cli import" not in src
    assert "import acid_engine.cli\n" not in src
    assert "from acid_engine.cli_judge import" in src


def test_cli_judge_has_no_argparse():
    from pathlib import Path

    import acid_engine.cli_judge as cli_judge

    src = Path(cli_judge.__file__).read_text(encoding="utf-8")
    assert "import argparse" not in src
    assert "add_parser" not in src
    assert "ArgumentParser" not in src


def test_cli_judge_hash_mismatch_is_runtime_hash():
    from acid_engine.level2.conformance import ConformanceStatus
    from acid_engine.worker import verify_runtime_pin

    payload = dump_script_lock(_script())
    tool = dict(payload["toolchain"])
    hashes = dict(tool["runtime_hashes"])
    hashes["acid_engine/cli_judge.py"] = "0" * 64
    tool["runtime_hashes"] = hashes
    bad = dict(payload)
    bad["toolchain"] = tool
    pin = verify_runtime_pin(bad)
    assert pin is not None
    assert pin.status == ConformanceStatus.FAIL
    assert pin.failure is not None
    assert pin.failure.property_name == "runtime_hash"
    assert pin.failure.detail == "acid_engine/cli_judge.py"


