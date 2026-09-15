"""After seal, a disk write to helper.py must not change what runs."""
from __future__ import annotations

from pathlib import Path

from acid_engine.cli import load_script_from_file
from acid_engine.level2.local_deps import seal_local_deps
from acid_engine.level3.script.resolve import materialize_script


def test_seal_lazy_helper_ignores_later_disk_write(tmp_path: Path) -> None:
    helper = tmp_path / "helper.py"
    helper.write_text("def process(d):\n    return {'r': 1}\n", encoding="utf-8")
    entry = tmp_path / "entry.py"
    entry.write_text(
        """
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
""",
        encoding="utf-8",
    )
    script = materialize_script(load_script_from_file(entry))
    assert seal_local_deps(script.implementation) is None
    helper.write_text("def process(d):\n    return {'r': 999}\n", encoding="utf-8")
    assert script.implementation({"n": 0}) == {"r": 1}
