import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "acid_engine"] + list(args),
        capture_output=True, text=True,
    )
    return result

def test_cli_help():
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "judge" in result.stdout
    assert "usage: acid-judge" in result.stdout
    assert "lock" in result.stdout
    assert "receipt" in result.stdout
    assert "diff" in result.stdout
    help_text = result.stdout
    assert "init" not in help_text
    assert "validate" not in help_text
    braces = [line for line in help_text.splitlines() if "{" in line and "}" in line]
    assert braces, help_text
    assert "run" not in braces[0]


def test_hidden_commands_are_gone():
    for name in ("init", "validate", "run"):
        result = _run_cli(name)
        assert result.returncode != 0
        text = result.stdout + result.stderr
        assert "invalid choice" in text or "unrecognized" in text or "error" in text.lower()
        assert "PASS" not in result.stdout


def test_cli_judge_help():
    result = _run_cli("judge", "--help")
    assert result.returncode == 0
    assert "--script" in result.stdout
    assert "--plan" in result.stdout
    assert "--agent" in result.stdout
    assert "--repository" in result.stdout


def test_cli_judge_requires_script():
    result = _run_cli("judge", "--input", "1")
    assert result.returncode != 0
    assert "ERROR" in result.stdout


def test_cli_judge_without_plan_is_skipped():
    script_code = '''from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level3.script.module import ScriptModule
script = ScriptModule(
    contract_id=ContractId("demo", "inc"),
    version=Version(0, 1, 0),
    specification=Specification(policy=Policy(pure=True, max_latency_ms=100)),
    input_type="int",
    output_type="int",
    implementation=lambda x: x + 1,
    name="inc",
)
'''
    with tempfile.TemporaryDirectory() as tmp:
        script_file = os.path.join(tmp, "inc.py")
        with open(script_file, "w") as f:
            f.write(script_code)
        result = _run_cli("judge", "--script", script_file, "--input", "5")
        assert result.returncode != 0
        assert "SKIPPED" in result.stdout

def test_cli_judge_runtime_mismatch_fails_before_pass():
    root = Path(__file__).parent.parent.parent
    plan = json.loads(
        (root / "examples" / "bones" / "n_plus_one.plan.json").read_text(encoding="utf-8")
    )
    plan["toolchain"]["runtime_hashes"][
        "acid_engine/level2/implementation_canon.py"
    ] = "0" * 64
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "bad.plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "acid_engine",
                "judge",
                "--script",
                str(root / "examples" / "bones" / "n_plus_one.json"),
                "--plan",
                str(plan_path),
                "--input",
                '{"n": 3}',
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(root),
        )
    assert result.returncode != 0
    assert "PASS" not in result.stdout
    assert "runtime_hash" in result.stdout
    assert "runtime: pinned" not in result.stdout
    assert "Execution blocked" in result.stdout
    assert "was not executed" in result.stdout


def test_cli_diff_bones_match():
    root = Path(__file__).parent.parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_engine",
            "diff",
            "--script",
            str(root / "examples" / "bones" / "n_plus_one.json"),
            "--plan",
            str(root / "examples" / "bones" / "n_plus_one.plan.json"),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(root),
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "MATCH" in result.stdout
    assert "PASS" not in result.stdout
    assert "The body was not executed." in result.stdout
