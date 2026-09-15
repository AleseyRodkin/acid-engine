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
    assert swapped.returncode == 0, swapped.stderr + swapped.stdout
    assert "PASS" in swapped.stdout
    assert "3330" in swapped.stdout

