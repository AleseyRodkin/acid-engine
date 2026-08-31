"""Rust judge: bind → python worker → verdict. No worker → SKIPPED, not PASS."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from examples.bones.n_plus_one import build_script

ROOT = Path(__file__).resolve().parents[2]
CRATE = ROOT / "rust" / "acid-judge"
BIN = CRATE / "target" / "debug" / "acid-judge"
BONES_JSON = ROOT / "examples" / "bones" / "n_plus_one.json"
BONES_PLAN = ROOT / "examples" / "bones" / "n_plus_one.plan.json"


def _ensure_bin() -> Path:
    if shutil.which("cargo") is None:
        pytest.skip("cargo not available")
    built = subprocess.run(
        ["cargo", "build", "--quiet"],
        cwd=str(CRATE),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    assert built.returncode == 0, built.stderr + built.stdout
    assert BIN.exists()
    return BIN


def rust_judge(payload: dict) -> dict:
    proc = subprocess.run(
        [str(_ensure_bin())],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(proc.stdout)


def test_rust_without_worker_is_skipped_not_pass():
    script = build_script()
    rust = rust_judge(
        {
            "module_hashes": {script.name: script.content_hash},
            "script_name": script.name,
            "script_hash": script.content_hash,
            "observation": {"status": "completed"},
            "output_type": script.output_type,
            "data": {"n": 4},
            "pure": True,
            "effects": [],
        }
    )
    assert rust["status"] == "SKIPPED"
    assert rust["status"] != "PASS"


def test_rust_mismatch_without_worker_is_skipped_not_fail():
    script = build_script()
    rust = rust_judge(
        {
            "module_hashes": {script.name: script.content_hash},
            "script_name": script.name,
            "script_hash": "0" * 64,
            "observation": {"status": "completed"},
            "output_type": "dict",
            "data": {"n": 4},
        }
    )
    assert rust["status"] == "SKIPPED"
    assert rust.get("property") != "module_hash"


def test_rust_empty_request_skipped():
    rust = rust_judge({})
    assert rust["status"] == "SKIPPED"


def test_rust_worker_bones_pass():
    plan = json.loads(BONES_PLAN.read_text(encoding="utf-8"))
    rust = rust_judge(
        {
            "module_hashes": dict(plan["module_hashes"]),
            "worker": {
                "python": sys.executable,
                "script": str(BONES_JSON),
                "input": {"n": 3},
                "cwd": str(ROOT),
            },
        }
    )
    assert rust["status"] == "PASS", rust
    assert rust.get("data") == {"n": 4}


def test_rust_worker_swapped_lock_fail_not_run_pass():
    rust = rust_judge(
        {
            "module_hashes": {"n_plus_one": "0" * 64},
            "worker": {
                "python": sys.executable,
                "script": str(BONES_JSON),
                "input": {"n": 3},
                "cwd": str(ROOT),
            },
        }
    )
    assert rust["status"] == "FAIL"
    assert rust.get("property") == "module_hash"
    assert "data" not in rust or rust["data"] is None
