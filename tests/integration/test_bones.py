"""Фикстура костей: dict n:3 → n:4 через execute_plan и JSON-почерк."""
import os
import subprocess
import sys
from pathlib import Path

from acid_engine.level2.blank_loader import load_script_blank
from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level3.pipeline import Pipeline
from acid_engine.level3.script.runner import execute_plan, lock_for_script
from examples.bones.n_plus_one import build_script, bump_n

ROOT = Path(__file__).parent.parent.parent
BONES = ROOT / "examples" / "bones"


def test_bump_n_unit():
    assert bump_n({"n": 3}) == {"n": 4}


def test_bones_main():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, str(BONES / "n_plus_one.py")],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS" in result.stdout
    assert "plan.lock" in result.stdout


def test_bones_execute_plan_and_pipeline():
    script = build_script()
    iface, plan = lock_for_script(script)
    step = execute_plan(iface, plan, script, {"n": 3})
    assert step.ok
    assert step.data == {"n": 4}
    pipe = Pipeline(script)
    out = pipe.execute({"n": 3})
    assert out.ok
    assert out.data == {"n": 4}


def test_json_and_py_same_hash_and_run():
    native = build_script()
    loaded = load_script_blank(BONES / "n_plus_one.json")
    assert loaded.content_hash == native.content_hash
    iface, plan = lock_for_script(loaded)
    step = execute_plan(iface, plan, loaded, {"n": 3})
    assert step.status == ConformanceStatus.PASS
    assert step.data == {"n": 4}


def test_cli_run_bones_json():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    plan = BONES / "n_plus_one.plan.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_engine",
            "run",
            "--script",
            str(BONES / "n_plus_one.json"),
            "--plan",
            str(plan),
            "--input",
            '{"n": 3}',
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS" in result.stdout
    assert "output: {'n': 4}" in result.stdout
