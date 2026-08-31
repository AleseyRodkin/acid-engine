import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from acid_engine.cli import load_script_from_file
from acid_engine.level2.blank_loader import load_script_blank
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level2.specification import Specification
from acid_engine.level3.script.module import ScriptModule

PY_BODY = """def plus_one(x):
    return x + 1
"""


def plus_one(x):
    return x + 1


def _write_pair(tmp: str, latency=None):
    py = Path(tmp) / "plus.py"
    py.write_text(PY_BODY, encoding="utf-8")
    spec = None
    if latency is not None:
        spec = {
            "parameters": {"values": {}},
            "policy": {
                "pure": False,
                "max_latency_ms": latency,
                "history": "none",
                "network": "forbidden",
                "security": "restricted",
                "quality_gate": None,
            },
            "implementation_requirements": {
                "required_methods": [],
                "required_exports": [],
                "required_signatures": [],
            },
        }
    doc = {
        "schema": "acid.blank.script.v1",
        "kind": "script",
        "contract_id": "t/plus",
        "version": "0.1.0",
        "name": "plus",
        "input_type": "int",
        "output_type": "int",
        "implementation": {
            "language": "python",
            "file": "plus.py",
            "entry": "plus_one",
        },
    }
    if spec is not None:
        doc["specification"] = spec
    js = Path(tmp) / "plus.json"
    js.write_text(json.dumps(doc), encoding="utf-8")
    return py, js


def test_json_and_callable_same_hash():
    with tempfile.TemporaryDirectory() as tmp:
        _py, js = _write_pair(tmp)
        loaded = load_script_blank(js)
        native = ScriptModule(
            contract_id=ContractId("t", "plus"),
            version=Version(0, 1, 0),
            specification=Specification(),
            input_type="int",
            output_type="int",
            implementation=plus_one,
            name="plus",
        )
        assert loaded.content_hash == native.content_hash
        assert loaded.implementation(4) == 5


def test_max_latency_ms_json_int_becomes_float():
    assert content_hash_of({"max_latency_ms": 200}) != content_hash_of(
        {"max_latency_ms": 200.0}
    )
    with tempfile.TemporaryDirectory() as tmp:
        _py, js = _write_pair(tmp, latency=200)
        loaded = load_script_blank(js)
        assert type(loaded.specification.policy.max_latency_ms) is float
        assert loaded.specification.policy.max_latency_ms == 200.0


def test_markdown_rejected():
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("# hi")
        path = f.name
    try:
        load_script_from_file(path)
        assert False, "md must be rejected"
    except ValueError as e:
        assert "markdown" in str(e).lower()
    finally:
        os.unlink(path)


def test_unknown_json_key_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        _py, js = _write_pair(tmp)
        data = json.loads(Path(js).read_text())
        data["extra"] = 1
        Path(js).write_text(json.dumps(data))
        try:
            load_script_blank(js)
            assert False
        except ValueError as e:
            assert "unknown key" in str(e)


def test_body_hash_mismatch_before_run():
    with tempfile.TemporaryDirectory() as tmp:
        _py, js = _write_pair(tmp)
        data = json.loads(Path(js).read_text())
        data["implementation"]["body_hash"] = "0" * 64
        Path(js).write_text(json.dumps(data))
        try:
            load_script_blank(js)
            assert False
        except ValueError as e:
            assert "body_hash" in str(e)


def test_cli_run_json_script():
    root = Path(__file__).parent.parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        _py, js = _write_pair(tmp)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        result = subprocess.run(
            [sys.executable, "-m", "acid_engine", "run", "--script", str(js), "--input", "3"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(root),
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "PASS" in result.stdout
        assert "output: 4" in result.stdout
