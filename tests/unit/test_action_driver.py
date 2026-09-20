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


def _tiny_index(tmp_path: Path) -> Path:
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
