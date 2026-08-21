import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from acid_engine.cli import parse_cli_input, load_script_from_file


def test_parse_cli_input_int():
    assert parse_cli_input("42") == 42
    assert parse_cli_input(None) == 3
    assert parse_cli_input("") == 3


def test_parse_cli_input_json_list():
    assert parse_cli_input("[1, 2, 3]") == [1, 2, 3]
    assert parse_cli_input('{"a": 1}') == {"a": 1}


def test_parse_cli_input_string():
    assert parse_cli_input("hello") == "hello"


def test_run_script_json_input():
    root = Path(__file__).parent.parent.parent
    script = '''
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level3.script.module import ScriptModule

script = ScriptModule(
    contract_id=ContractId("cli", "sum_list"),
    version=Version(0, 1, 0),
    specification=Specification(policy=Policy(max_latency_ms=100)),
    input_type="list",
    output_type="int",
    implementation=lambda xs: sum(xs),
    name="sum_list",
)
'''
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(script)
        path = f.name
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        result = subprocess.run(
            [sys.executable, "-m", "acid_engine", "run", "--script", path, "--input", "[10, 20, 12]"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(root),
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "PASS" in result.stdout
        assert "output: 42" in result.stdout
    finally:
        os.unlink(path)


def test_load_script_missing_raises():
    try:
        load_script_from_file("/tmp/does_not_exist_acid.py")
        assert False, "should raise"
    except FileNotFoundError:
        pass
