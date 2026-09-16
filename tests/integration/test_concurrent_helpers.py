"""Two tools, both with helper.py: concurrent judge must not PASS the other's body."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from acid_engine.cli import load_script_from_file
from acid_engine.judge import judge_script
from acid_engine.level2.local_deps import seal_local_deps
from acid_engine.level3.script.resolve import materialize_script
from acid_engine.level3.script.runner import dump_script_lock, load_script_lock

ENTRY = '''
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def entry(data):
    from helper import process
    return process(data)


script = ScriptModule(
    contract_id=ContractId("t", "entry"),
    version=Version(0, 1, 0),
    specification=Specification(policy=Policy()),
    input_type="dict",
    output_type="dict",
    implementation=entry,
    name="entry",
)
'''


def _make_tool(root: Path, marker: int) -> Path:
    root.mkdir()
    (root / "helper.py").write_text(
        f"def process(d):\n    return {{'r': {marker}}}\n",
        encoding="utf-8",
    )
    entry = root / "entry.py"
    entry.write_text(ENTRY, encoding="utf-8")
    return entry


def test_seal_does_not_bind_bare_helper_name(tmp_path: Path) -> None:
    sys.modules.pop("helper", None)
    entry = _make_tool(tmp_path / "t", 7)
    script = materialize_script(load_script_from_file(entry))
    assert seal_local_deps(script.implementation) is None
    assert "helper" not in sys.modules
    assert script.implementation({"n": 0}) == {"r": 7}


def test_concurrent_same_named_helpers_do_not_cross(tmp_path: Path) -> None:
    script_a = materialize_script(load_script_from_file(_make_tool(tmp_path / "a", 1)))
    script_b = materialize_script(load_script_from_file(_make_tool(tmp_path / "b", 2)))
    payload_a = dump_script_lock(script_a)
    payload_b = dump_script_lock(script_b)
    assert "dep:helper.py" in payload_a["module_hashes"]
    assert payload_a["module_hashes"]["dep:helper.py"] != payload_b["module_hashes"]["dep:helper.py"]

    crosses: list[str] = []
    barrier = threading.Barrier(2)

    def worker(script: object, payload: dict, expect: int) -> None:
        iface, plan = load_script_lock(payload)
        barrier.wait()
        for _ in range(150):
            result = judge_script(
                script, {"n": 0}, plan=plan, iface=iface, toolchain=payload
            )
            if not result.ok:
                crosses.append(f"not PASS expect={expect} {result.message}")
                return
            if result.data != {"r": expect}:
                crosses.append(f"crossed expect={expect} got={result.data!r}")
                return

    threads = [
        threading.Thread(target=worker, args=(script_a, payload_a, 1)),
        threading.Thread(target=worker, args=(script_b, payload_b, 2)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert crosses == []
