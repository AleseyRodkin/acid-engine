"""Live pin: argparse/help in cli.py is not contour; cli_judge.py / worker.py are."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "examples" / "tools" / "compute_amount.py"
PLAN = ROOT / "examples" / "tools" / "compute_amount.plan.json"
INCOMING = '{"cents": 1999, "qty": 2}'


def _tree(tmp: Path) -> Path:
    root = tmp / "tree"
    shutil.copytree(
        ROOT / "acid_engine",
        root / "acid_engine",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    tools = root / "examples" / "tools"
    tools.mkdir(parents=True)
    shutil.copy2(SRC, tools / "compute_amount.py")
    shutil.copy2(PLAN, tools / "compute_amount.plan.json")
    return root


def _judge(root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_engine",
            "judge",
            "--script",
            str(root / "examples" / "tools" / "compute_amount.py"),
            "--plan",
            str(root / "examples" / "tools" / "compute_amount.plan.json"),
            "--input",
            INCOMING,
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(root),
    )


def test_honest_copy_passes(tmp_path: Path):
    proc = _judge(_tree(tmp_path))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS" in proc.stdout


def test_body_swap_honest_cli_is_source_hash_fail(tmp_path: Path):
    root = _tree(tmp_path)
    script = root / "examples" / "tools" / "compute_amount.py"
    original = script.read_text(encoding="utf-8")
    script.write_text(original.replace("cents * qty", "cents * qty + 1", 1), encoding="utf-8")
    proc = _judge(root)
    assert proc.returncode != 0
    assert "source_hash" in proc.stdout
    assert "PASS" not in proc.stdout
    assert "was not imported" in proc.stdout or "was not executed" in proc.stdout


def test_help_patch_in_cli_py_is_not_runtime_hash(tmp_path: Path):
    root = _tree(tmp_path)
    cli = root / "acid_engine" / "cli.py"
    text = cli.read_text(encoding="utf-8")
    cli.write_text(text.replace("lock, judge, receipt.", "lock, judge, receipt. help patch."), encoding="utf-8")
    proc = _judge(root)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS" in proc.stdout
    assert "runtime_hash" not in proc.stdout
    assert "worker_hash" not in proc.stdout


def test_cli_judge_byte_patch_is_runtime_hash_fail(tmp_path: Path):
    root = _tree(tmp_path)
    path = root / "acid_engine" / "cli_judge.py"
    path.write_bytes(path.read_bytes() + b"\n")
    proc = _judge(root)
    assert proc.returncode != 0
    assert "PASS" not in proc.stdout
    assert "runtime_hash" in proc.stdout
    assert "was not executed" in proc.stdout or "Execution blocked" in proc.stdout


def test_worker_byte_patch_fails_before_run(tmp_path: Path):
    root = _tree(tmp_path)
    path = root / "acid_engine" / "worker.py"
    path.write_bytes(path.read_bytes() + b"\n")
    proc = _judge(root)
    assert proc.returncode != 0
    assert "PASS" not in proc.stdout
    assert "worker_hash" in proc.stdout or "runtime_hash" in proc.stdout
    assert "was not executed" in proc.stdout or "Execution blocked" in proc.stdout


def test_action_driver_byte_patch_is_runtime_hash_fail(tmp_path: Path):
    root = _tree(tmp_path)
    path = root / "acid_engine" / "action_driver.py"
    path.write_bytes(path.read_bytes() + b"\n")
    proc = _judge(root)
    assert proc.returncode != 0
    assert "PASS" not in proc.stdout
    assert "runtime_hash" in proc.stdout
    assert "was not executed" in proc.stdout or "Execution blocked" in proc.stdout


def test_cmd_judge_lives_in_cli_judge():
    from acid_engine import cli, cli_judge

    assert cli.cmd_judge is cli_judge.cmd_judge
