"""Local imports of a tool are pinned. Swapping helper.py is FAIL before run."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _write_pair(tmp: Path, helper_body: str) -> tuple[Path, Path]:
    helper = tmp / "helper.py"
    helper.write_text(helper_body, encoding="utf-8")
    entry = tmp / "entry.py"
    entry.write_text(
        """
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule
from helper import process


def entry(data):
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
    return entry, helper


def _cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-m", "acid_engine", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd),
    )


def test_helper_swap_fails_before_pass(tmp_path: Path):
    entry, _helper = _write_pair(
        tmp_path,
        "def process(d):\n    return {'r': d.get('n', 0) * 2}\n",
    )
    plan = tmp_path / "entry.plan.json"
    lock = _cli("lock", "--script", str(entry), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    assert "local imports pinned: 1" in lock.stdout
    payload = json.loads(plan.read_text(encoding="utf-8"))
    assert payload["dependency_hashes"]["helper.py"]
    assert payload["module_hashes"]["dep:helper.py"] == payload["dependency_hashes"]["helper.py"]
    honest = _cli(
        "judge",
        "--script",
        str(entry),
        "--plan",
        str(plan),
        "--input",
        '{"n": 5}',
        cwd=tmp_path,
    )
    assert honest.returncode == 0, honest.stderr + honest.stdout
    assert "PASS" in honest.stdout
    assert "{'r': 10}" in honest.stdout or '"r": 10' in honest.stdout
    _helper = tmp_path / "helper.py"
    _helper.write_text("def process(d):\n    return {'r': 4995}\n", encoding="utf-8")
    swapped = _cli(
        "judge",
        "--script",
        str(entry),
        "--plan",
        str(plan),
        "--input",
        '{"n": 5}',
        cwd=tmp_path,
    )
    assert swapped.returncode != 0
    assert "PASS" not in swapped.stdout
    assert "dependency_hash" in swapped.stdout
    assert "was not executed" in swapped.stdout
    assert "4995" not in swapped.stdout
    assert "helper.py" in swapped.stdout
    assert "['helper.py']" not in swapped.stdout
    assert "expected='missing'" not in swapped.stdout
    assert "actual='missing'" not in swapped.stdout


def test_dynamic_import_lock_warns_and_does_not_pin(tmp_path: Path):
    helper = tmp_path / "helper.py"
    helper.write_text("def process(d):\n    return {'r': 1}\n", encoding="utf-8")
    entry = tmp_path / "entry.py"
    entry.write_text(
        """
import importlib
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def entry(data):
    helper = importlib.import_module("helper")
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
    plan = tmp_path / "entry.plan.json"
    lock = _cli("lock", "--script", str(entry), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    assert "local imports pinned: 0" in lock.stdout
    assert "dynamic import" in lock.stdout
    assert "importlib.import_module" in lock.stdout
    assert "cannot be fully pinned" in lock.stdout
    payload = json.loads(plan.read_text(encoding="utf-8"))
    assert payload["dependency_hashes"] == {}
    helper.write_text("def process(d):\n    return {'r': 3330}\n", encoding="utf-8")
    swapped = _cli(
        "judge",
        "--script",
        str(entry),
        "--plan",
        str(plan),
        "--input",
        '{"n": 1}',
        cwd=tmp_path,
    )
    assert swapped.returncode != 0
    assert "PASS" not in swapped.stdout
    assert "3330" not in swapped.stdout
    assert "dynamic" in swapped.stdout.lower()


def test_allow_dynamic_is_0_2_32(tmp_path: Path):
    helper = tmp_path / "helper.py"
    helper.write_text("def process(d):\n    return {'r': 1}\n", encoding="utf-8")
    entry = tmp_path / "entry.py"
    entry.write_text(
        """
import importlib
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def entry(data):
    helper = importlib.import_module("helper")
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
    plan = tmp_path / "entry.plan.json"
    lock = _cli("lock", "--script", str(entry), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    payload = json.loads(plan.read_text(encoding="utf-8"))
    payload["allow_dynamic"] = True
    plan.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    helper.write_text("def process(d):\n    return {'r': 3330}\n", encoding="utf-8")
    swapped = _cli(
        "judge",
        "--script",
        str(entry),
        "--plan",
        str(plan),
        "--input",
        '{"n": 1}',
        cwd=tmp_path,
    )
    assert swapped.returncode == 0, swapped.stderr + swapped.stdout
    assert "PASS" in swapped.stdout
    assert "3330" in swapped.stdout


def _write_pkg_tool(tmp: Path, init_body: str) -> tuple[Path, Path]:
    pkg = tmp / "pkg"
    pkg.mkdir()
    init = pkg / "__init__.py"
    init.write_text(init_body, encoding="utf-8")
    entry = tmp / "entry.py"
    entry.write_text(
        """
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def entry(data):
    from pkg import process
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
    return entry, init


def test_package_init_lock_key_is_file_path(tmp_path: Path):
    from acid_engine.level2.local_deps import _import_name

    assert _import_name("pkg/__init__.py") == "pkg"
    assert _import_name("pkg/sub.py") == "pkg.sub"
    entry, _init = _write_pkg_tool(
        tmp_path,
        "def process(d):\n    return {'r': d.get('n', 0) * 2}\n",
    )
    plan = tmp_path / "entry.plan.json"
    lock = _cli("lock", "--script", str(entry), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    payload = json.loads(plan.read_text(encoding="utf-8"))
    assert "pkg/__init__.py" in payload["dependency_hashes"]
    assert payload["module_hashes"]["dep:pkg/__init__.py"] == payload["dependency_hashes"][
        "pkg/__init__.py"
    ]
    assert "dep:pkg.__init" not in payload["module_hashes"]
    assert "dep:pkg" not in payload["module_hashes"]
    honest = _cli(
        "judge",
        "--script",
        str(entry),
        "--plan",
        str(plan),
        "--input",
        '{"n": 5}',
        cwd=tmp_path,
    )
    assert honest.returncode == 0, honest.stderr + honest.stdout
    assert "PASS" in honest.stdout
    (tmp_path / "pkg" / "__init__.py").write_text(
        "def process(d):\n    return {'r': 4995}\n",
        encoding="utf-8",
    )
    swapped = _cli(
        "judge",
        "--script",
        str(entry),
        "--plan",
        str(plan),
        "--input",
        '{"n": 5}',
        cwd=tmp_path,
    )
    assert swapped.returncode != 0
    assert "PASS" not in swapped.stdout
    assert "4995" not in swapped.stdout
    assert "pkg/__init__.py" in swapped.stdout


def test_package_init_seal_overwrite_is_not_new_bytes(tmp_path: Path):
    from acid_engine.cli import load_script_from_file
    from acid_engine.level2.local_deps import seal_local_deps
    from acid_engine.level3.script.resolve import materialize_script

    entry, init = _write_pkg_tool(
        tmp_path,
        "def process(d):\n    return {'r': 1}\n",
    )
    script = materialize_script(load_script_from_file(entry))
    assert seal_local_deps(script.implementation) is None
    init.write_text("def process(d):\n    return {'r': 999}\n", encoding="utf-8")
    assert script.implementation({"n": 0}) == {"r": 1}


def test_from_pkg_import_sub_seal_overwrite_is_not_new_bytes(tmp_path: Path):
    from acid_engine.cli import load_script_from_file
    from acid_engine.level2.local_deps import seal_local_deps
    from acid_engine.level3.script.resolve import materialize_script

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("# pkg\n", encoding="utf-8")
    sub = pkg / "sub.py"
    sub.write_text("def process(d):\n    return {'r': 2}\n", encoding="utf-8")
    entry = tmp_path / "entry.py"
    entry.write_text(
        """
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def entry(data):
    from pkg import sub
    return sub.process(data)


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
    plan = tmp_path / "entry.plan.json"
    lock = _cli("lock", "--script", str(entry), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    payload = json.loads(plan.read_text(encoding="utf-8"))
    assert "pkg/__init__.py" in payload["dependency_hashes"]
    assert "pkg/sub.py" in payload["dependency_hashes"]
    assert seal_local_deps(script.implementation) is None
    sub.write_text("def process(d):\n    return {'r': 7777}\n", encoding="utf-8")
    assert script.implementation({"n": 0}) == {"r": 2}
    swapped = _cli(
        "judge",
        "--script",
        str(entry),
        "--plan",
        str(plan),
        "--input",
        '{"n": 0}',
        cwd=tmp_path,
    )
    assert swapped.returncode != 0
    assert "PASS" not in swapped.stdout
    assert "7777" not in swapped.stdout


def _write_cycle_tool(tmp: Path, *, a_prefix: str = "", b_body: str) -> Path:
    (tmp / "a.py").write_text(
        a_prefix + "import b\n\ndef process(d):\n    return {'r': b.value}\n",
        encoding="utf-8",
    )
    (tmp / "b.py").write_text(b_body, encoding="utf-8")
    entry = tmp / "entry.py"
    entry.write_text(
        """
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def entry(data):
    from a import process
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
    return entry


def test_cycle_overwrite_after_seal_is_not_new_bytes(tmp_path: Path):
    from acid_engine.cli import load_script_from_file
    from acid_engine.level2.local_deps import seal_local_deps
    from acid_engine.level3.script.resolve import materialize_script

    entry = _write_cycle_tool(
        tmp_path, b_body="import a\nvalue = 1\n"
    )
    script = materialize_script(load_script_from_file(entry))
    assert seal_local_deps(script.implementation) is None
    (tmp_path / "b.py").write_text("import a\nvalue = 999\n", encoding="utf-8")
    (tmp_path / "a.py").write_text(
        "import b\n\ndef process(d):\n    return {'r': 888}\n",
        encoding="utf-8",
    )
    assert script.implementation({"n": 0}) == {"r": 1}


def test_mismatch_does_not_exec_good_neighbor(tmp_path: Path):
    from acid_engine.cli import load_script_from_file
    from acid_engine.level2.local_deps import seal_local_deps
    from acid_engine.level3.script.resolve import materialize_script
    from acid_engine.level3.script.runner import dump_script_lock

    marker = tmp_path / "good_ran"
    entry = _write_cycle_tool(
        tmp_path,
        a_prefix=f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
        b_body="import a\nvalue = 1\n",
    )
    script = materialize_script(load_script_from_file(entry))
    payload = dump_script_lock(script)
    locked = payload["dependency_hashes"]
    marker.unlink(missing_ok=True)
    (tmp_path / "b.py").write_text("import a\nvalue = 999\n", encoding="utf-8")
    leaked = seal_local_deps(script.implementation, locked=locked)
    assert leaked == "b.py"
    assert not marker.exists()
