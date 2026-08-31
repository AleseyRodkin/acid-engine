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
    assert "lock" in result.stdout


def test_cli_judge_help():
    result = _run_cli("judge", "--help")
    assert result.returncode == 0
    assert "--script" in result.stdout
    assert "--plan" in result.stdout


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

def test_cli_init():
    with tempfile.TemporaryDirectory() as tmp:
        # markdown path is redirected: init writes a .py script, not dead markdown
        md_path = os.path.join(tmp, "test_spec.md")
        result = _run_cli("init", "--path", md_path)
        assert result.returncode == 0
        # cwd is repo root; script.py is written there when .md requested
        # prefer explicit --script target
        script_file = os.path.join(tmp, "demo_script.py")
        result2 = _run_cli("init", "--script", script_file)
        assert result2.returncode == 0
        assert os.path.exists(script_file)
        body = Path(script_file).read_text()
        assert "ScriptModule" in body
        assert "script =" in body

def test_cli_run_walking_skeleton():
    result = _run_cli("run")
    assert result.returncode == 0
    assert "PASS" in result.stdout

def test_cli_validate():
    contract_code = '''from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level2.identity import ContractId, Version
contract = InterfaceContract(
    contract_id=ContractId("test", "echo"),
    version=Version(1,0,0),
    inputs={},
    outputs={"result": "dict"},
    constraints={"semantic_rules": {"contains": "hello"}},
)
'''
    with tempfile.TemporaryDirectory() as tmp:
        contract_file = os.path.join(tmp, "contract.py")
        with open(contract_file, "w") as f:
            f.write(contract_code)
        result = _run_cli("validate", contract_file, "echo", "hello")
        assert result.returncode == 0
        assert "[PASS]" in result.stdout


def test_cli_run_script():
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
        plan_file = os.path.join(tmp, "inc.plan.json")
        lock = _run_cli("lock", "--script", script_file, "--out", plan_file)
        assert lock.returncode == 0, lock.stderr + lock.stdout
        result = _run_cli("run", "--script", script_file, "--plan", plan_file, "--input", "5")
        assert result.returncode == 0, result.stderr + result.stdout
        assert "[PASS]" in result.stdout
        assert "output: 6" in result.stdout


def test_cli_run_script_without_plan_is_skipped():
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
        result = _run_cli("run", "--script", script_file, "--input", "5")
        assert result.returncode != 0
        assert "SKIPPED" in result.stdout
        assert "self-lock" in result.stdout.lower()


def test_cli_run_script_missing():
    result = _run_cli("run", "--script", "/no/such/script.py")
    assert result.returncode != 0
    assert "ERROR" in result.stdout


def test_cli_validate_rejects_markdown():
    with tempfile.TemporaryDirectory() as tmp:
        spec = os.path.join(tmp, "spec.md")
        Path(spec).write_text("# not a contract\n")
        result = _run_cli("validate", spec, "echo", "hello")
        assert result.returncode != 0
        assert "markdown" in result.stdout.lower() or "ERROR" in result.stdout
