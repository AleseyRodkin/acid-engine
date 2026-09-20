"""Action driver: empty index fails; mock binary PASS/FAIL; not in the pin."""
from __future__ import annotations

import json
import stat
from pathlib import Path

from acid_engine.action_driver import run
from acid_engine.worker import RUNTIME_PIN_PATHS


def _mock_bin(tmp_path: Path, status: str) -> Path:
    code = 0 if status == "PASS" else 1 if status == "FAIL" else 2
    path = tmp_path / f"mock-{status.lower()}"
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"print(json.dumps({{'status': {status!r}, 'message': 'mock', 'data': {{'n': 1}}}}))\n"
        f"raise SystemExit({code})\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def _tiny_index(tmp_path: Path, script: Path | None = None) -> Path:
    if script is None:
        script = tmp_path / "tool.py"
        script.write_text("x = 1\n", encoding="utf-8")
    plan = tmp_path / "tool.plan.json"
    plan.write_text(
        json.dumps(
            {
                "module_hashes": {"tool": "ab"},
                "source_hash": "cd",
                "toolchain": {"worker_hash": "w", "runtime_hashes": {}},
            }
        ),
        encoding="utf-8",
    )
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "id": "tool",
                        "script": str(script),
                        "plan": str(plan),
                        "input": {"n": 1},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return index


def test_driver_in_runtime_pin():
    assert "acid_engine/action_driver.py" in RUNTIME_PIN_PATHS
    assert len(RUNTIME_PIN_PATHS) == 8


def test_driver_source_does_not_reload_script():
    from acid_engine import action_driver

    src = Path(action_driver.__file__).read_text(encoding="utf-8")
    assert "load_script_from_file" not in src


def test_empty_index_is_nonzero(tmp_path: Path):
    index = tmp_path / "index.json"
    index.write_text(json.dumps({"entries": []}), encoding="utf-8")
    rc = run(_mock_bin(tmp_path, "PASS"), index, tmp_path / "receipts")
    assert rc != 0


def test_mock_binary_pass_writes_receipt(tmp_path: Path):
    receipts = tmp_path / "receipts"
    rc = run(_mock_bin(tmp_path, "PASS"), _tiny_index(tmp_path), receipts)
    assert rc == 0
    rec = receipts / "tool.json"
    assert rec.is_file()
    payload = json.loads(rec.read_text(encoding="utf-8"))
    assert payload["verdict"]["status"] == "PASS"
    assert "proven_pure" not in json.dumps(payload)


def test_mock_binary_fail_is_nonzero(tmp_path: Path):
    receipts = tmp_path / "receipts"
    rc = run(_mock_bin(tmp_path, "FAIL"), _tiny_index(tmp_path), receipts)
    assert rc != 0
    payload = json.loads((receipts / "tool.json").read_text(encoding="utf-8"))
    assert payload["verdict"]["status"] == "FAIL"


def test_driver_pass_does_not_exec_tool_module(tmp_path: Path):
    marker = tmp_path / "loaded"
    script = tmp_path / "tool.py"
    script.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('loaded')\n"
        "from acid_engine.level2.identity import ContractId, Version\n"
        "from acid_engine.level2.specification import Policy, Specification\n"
        "from acid_engine.level3.script.module import ScriptModule\n"
        "def entry(data):\n    return data\n"
        "script = ScriptModule(\n"
        "    contract_id=ContractId('t', 'tool'),\n"
        "    version=Version(0, 1, 0),\n"
        "    specification=Specification(policy=Policy()),\n"
        "    input_type='dict',\n"
        "    output_type='dict',\n"
        "    implementation=entry,\n"
        "    name='tool',\n"
        ")\n",
        encoding="utf-8",
    )
    receipts = tmp_path / "receipts"
    rc = run(_mock_bin(tmp_path, "PASS"), _tiny_index(tmp_path, script), receipts)
    assert rc == 0
    assert not marker.exists()
    payload = json.loads((receipts / "tool.json").read_text(encoding="utf-8"))
    assert payload["verdict"]["status"] == "PASS"
