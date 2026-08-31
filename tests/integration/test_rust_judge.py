"""Rust judge: тот же PASS/FAIL/SKIPPED, что Python, на костях и bind."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from acid_engine.judge import judge_script
from acid_engine.level2.conformance import ConformanceStatus
from examples.bones.n_plus_one import build_script
from examples.commerce.order_amounts import build_pipeline, lock_pair

ROOT = Path(__file__).resolve().parents[2]
CRATE = ROOT / "rust" / "acid-judge"
BIN = CRATE / "target" / "debug" / "acid-judge"


def _ensure_bin() -> Path:
    if shutil.which("cargo") is None:
        pytest.skip("cargo not available")
    if not BIN.exists():
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


def test_rust_bones_same_status_as_python():
    script = build_script()
    py = judge_script(script, {"n": 3})
    assert py.status == ConformanceStatus.PASS
    rust = rust_judge(
        {
            "module_hashes": {script.name: script.content_hash},
            "script_name": script.name,
            "script_hash": script.content_hash,
            "observation": {"status": py.observation.status},
            "output_type": script.output_type,
            "data": py.data,
            "pure": True,
            "effects": list(py.observation.effects_observed),
        }
    )
    assert rust["status"] == "PASS"


def test_rust_swapped_hash_fail():
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
    assert rust["status"] == "FAIL"
    assert rust.get("property") == "module_hash"


def test_rust_empty_hashes_skipped():
    rust = rust_judge(
        {
            "module_hashes": {},
            "script_name": "n_plus_one",
            "script_hash": "abc",
            "observation": {"status": "completed"},
            "output_type": "dict",
            "data": {"n": 4},
        }
    )
    assert rust["status"] == "SKIPPED"


def test_rust_commerce_filter_bind_matches_python():
    leaf_f, leaf_s = build_pipeline()[1:]
    iface, plan = lock_pair(leaf_f, leaf_s)
    py = judge_script(
        leaf_f.script, [15000, -200, True, 100], plan=plan, iface=iface
    )
    assert py.status == ConformanceStatus.PASS
    rust = rust_judge(
        {
            "module_hashes": dict(plan.module_hashes),
            "script_name": leaf_f.script.name,
            "script_hash": leaf_f.script.content_hash,
            "observation": {"status": py.observation.status},
            "output_type": leaf_f.script.output_type,
            "data": py.data,
            "pure": True,
            "effects": list(py.observation.effects_observed),
        }
    )
    assert rust["status"] == py.status.value
