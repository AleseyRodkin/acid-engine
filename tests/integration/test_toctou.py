"""After seal, a disk write to helper.py must not change what runs."""
from __future__ import annotations

import hashlib
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
    honest = b"def process(d):\n    return {'r': 1}\n"
    locked = {"helper.py": hashlib.sha256(honest).hexdigest()}
    assert seal_local_deps(script.implementation, locked=locked) == "helper.py"
    assert script.implementation({"n": 0}) == {"r": 1}


def test_undeclared_helper_after_lock_is_fail(tmp_path: Path) -> None:
    """Empty locked deps still walk: a helper that appears after lock is FAIL."""
    import os
    import subprocess
    import sys

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
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    plan = tmp_path / "entry.plan.json"
    lock = subprocess.run(
        [sys.executable, "-m", "acid_engine", "lock", "--script", str(entry), "--out", str(plan)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert lock.returncode == 0, lock.stderr + lock.stdout
    assert "local imports pinned: 0" in lock.stdout
    (tmp_path / "helper.py").write_text(
        "def process(d):\n    return {'r': 999}\n",
        encoding="utf-8",
    )
    judged = subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_engine",
            "judge",
            "--script",
            str(entry),
            "--plan",
            str(plan),
            "--input",
            '{"n": 0}',
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert judged.returncode != 0
    assert "PASS" not in judged.stdout
    assert "dependency" in judged.stdout.lower() or "helper.py" in judged.stdout


def _write_reload_tool(tmp: Path) -> tuple[Path, Path]:
    helper = tmp / "helper.py"
    helper.write_text("def process(d):\n    return {'r': 1}\n", encoding="utf-8")
    entry = tmp / "entry.py"
    entry.write_text(
        """
import helper
import importlib
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def entry(data):
    importlib.reload(helper)
    return helper.process(data)


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
    return entry, helper


def test_reload_after_seal_is_not_new_bytes(tmp_path: Path) -> None:
    """Module-level helper + importlib.reload after seal must not exec a later disk write."""
    import sys

    entry, helper = _write_reload_tool(tmp_path)
    sys.path.insert(0, str(tmp_path))
    sys.modules.pop("helper", None)
    try:
        script = materialize_script(load_script_from_file(entry))
        assert seal_local_deps(script.implementation) is None
        helper.write_text("def process(d):\n    return {'r': 999}\n", encoding="utf-8")
        assert script.implementation({"n": 0}) == {"r": 1}
    finally:
        sys.modules.pop("helper", None)
        if sys.path and sys.path[0] == str(tmp_path):
            sys.path.pop(0)


def test_reload_tool_static_swap_is_fail(tmp_path: Path) -> None:
    import os
    import subprocess
    import sys

    entry, helper = _write_reload_tool(tmp_path)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    plan = tmp_path / "entry.plan.json"
    lock = subprocess.run(
        [sys.executable, "-m", "acid_engine", "lock", "--script", str(entry), "--out", str(plan)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert lock.returncode == 0, lock.stderr + lock.stdout
    honest = subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_engine",
            "judge",
            "--script",
            str(entry),
            "--plan",
            str(plan),
            "--input",
            '{"n": 0}',
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert honest.returncode == 0, honest.stderr + honest.stdout
    assert "PASS" in honest.stdout
    helper.write_text("def process(d):\n    return {'r': 999}\n", encoding="utf-8")
    swapped = subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_engine",
            "judge",
            "--script",
            str(entry),
            "--plan",
            str(plan),
            "--input",
            '{"n": 0}',
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert swapped.returncode != 0
    assert "PASS" not in swapped.stdout
    assert "999" not in swapped.stdout
