import subprocess
import sys
from pathlib import Path
import tempfile
import os

def _run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "acid_engine"] + list(args),
        capture_output=True, text=True,
    )
    return result

def test_cli_help():
    result = _run_cli("--help")
    assert result.returncode == 0

def test_cli_init():
    with tempfile.TemporaryDirectory() as tmp:
        spec_file = os.path.join(tmp, "test_spec.md")
        result = _run_cli("init", "--path", spec_file)
        assert result.returncode == 0
        assert os.path.exists(spec_file)

def test_cli_run_walking_skeleton():
    result = _run_cli("run")
    assert result.returncode == 0
    assert "PASS" in result.stdout

def test_cli_validate():
    # Создаём временный Python-контракт
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