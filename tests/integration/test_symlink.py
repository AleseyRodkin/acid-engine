"""Symlink is followed. Swapping the target after lock is FAIL."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_BODY = """
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule

def entry(data):
    return {"r": %s}

script = ScriptModule(
    contract_id=ContractId("t", "entry"),
    version=Version(0, 1, 0),
    specification=Specification(policy=Policy()),
    input_type="dict",
    output_type="dict",
    implementation=entry,
    name="entry",
)
"""


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


def test_symlink_same_target_passes(tmp_path: Path) -> None:
    real = tmp_path / "real.py"
    real.write_text(_BODY % 1, encoding="utf-8")
    link = tmp_path / "tool.py"
    link.symlink_to(real)
    plan = tmp_path / "entry.plan.json"
    lock = _cli("lock", "--script", str(link), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    honest = _cli(
        "judge",
        "--script",
        str(link),
        "--plan",
        str(plan),
        "--input",
        "{}",
        cwd=tmp_path,
    )
    assert honest.returncode == 0, honest.stderr + honest.stdout
    assert "PASS" in honest.stdout


def test_symlink_retarget_fails(tmp_path: Path) -> None:
    real = tmp_path / "real.py"
    other = tmp_path / "other.py"
    real.write_text(_BODY % 1, encoding="utf-8")
    other.write_text(_BODY % 9, encoding="utf-8")
    link = tmp_path / "tool.py"
    link.symlink_to(real)
    plan = tmp_path / "entry.plan.json"
    lock = _cli("lock", "--script", str(link), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    link.unlink()
    link.symlink_to(other)
    swapped = _cli(
        "judge",
        "--script",
        str(link),
        "--plan",
        str(plan),
        "--input",
        "{}",
        cwd=tmp_path,
    )
    assert swapped.returncode != 0
    assert "PASS" not in swapped.stdout
    assert "module_hash" in swapped.stdout
