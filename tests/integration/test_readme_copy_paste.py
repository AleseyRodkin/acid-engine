"""Live CLI from README. No mocks. Without --plan is SKIPPED, not PASS."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _cli(*args: str, receipt: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    cmd = [sys.executable, "-m", "acid_engine", *args]
    if receipt is not None:
        cmd.extend(["--receipt", str(receipt)])
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )


def test_readme_lock_help():
    proc = _cli("lock", "--help")
    assert proc.returncode == 0, proc.stderr
    assert "--script" in proc.stdout
    assert "--out" in proc.stdout


def test_readme_bones_judge_pass_and_receipt(tmp_path: Path):
    rec = tmp_path / "bones.receipt.json"
    proc = _cli(
        "judge",
        "--script",
        "examples/bones/n_plus_one.json",
        "--plan",
        "examples/bones/n_plus_one.plan.json",
        "--input",
        '{"n": 3}',
        receipt=rec,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS" in proc.stdout
    assert "runtime: pinned" in proc.stdout
    assert "SKIPPED" not in proc.stdout
    assert "{'n': 4}" in proc.stdout or '"n": 4' in proc.stdout
    assert rec.is_file()
    payload = json.loads(rec.read_text(encoding="utf-8"))
    assert "proven_pure" not in json.dumps(payload)
    assert payload["verdict"]["status"] == "PASS"
    assert payload["output"] == {"n": 4}


def test_readme_bones_without_plan_skipped():
    proc = _cli(
        "judge",
        "--script",
        "examples/bones/n_plus_one.json",
        "--input",
        '{"n": 3}',
    )
    assert proc.returncode != 0
    assert "SKIPPED" in proc.stdout
    assert "PASS" not in proc.stdout
