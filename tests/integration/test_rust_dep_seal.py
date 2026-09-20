"""Supervisor last-mile: helper swap between identify and run is not PASS."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from acid_engine.level2.local_deps import _SEALED
from acid_engine.worker import handle, runtime_hashes, source_hash

ROOT = Path(__file__).resolve().parents[2]


def _write_pair(tmp: Path, helper_body: str) -> tuple[Path, Path]:
    helper = tmp / "helper.py"
    helper.write_text(helper_body, encoding="utf-8")
    entry = tmp / "entry.py"
    entry.write_text(
        """
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule
from helper import process


def entry(data):
    return process(data)


script = ScriptModule(
    contract_id=ContractId("t", "entry"),
    version=Version(0, 1, 0),
    specification=Specification(policy=Policy()),
    input_type="dict",
    output_type="dict",
    implementation=entry,
    name="entry",
)
""",
        encoding="utf-8",
    )
    return entry, helper


def _lock(tmp: Path, entry: Path) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    plan = tmp / "entry.plan.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "acid_engine",
            "lock",
            "--script",
            str(entry),
            "--out",
            str(plan),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(plan.read_text(encoding="utf-8"))


def _req(plan: dict, entry: Path, op: str, input_data: dict | None = None) -> dict:
    tool = plan.get("toolchain") or {}
    payload: dict = {
        "op": op,
        "script": str(entry),
        "source_hash": plan["source_hash"],
        "module_hashes": plan["module_hashes"],
        "dependency_hashes": plan.get("dependency_hashes") or {},
    }
    if op == "run":
        payload["input"] = input_data or {"n": 5}
    payload["worker_hash"] = tool.get("worker_hash")
    payload["runtime_hashes"] = tool.get("runtime_hashes")
    return payload


def test_worker_swap_helper_between_identify_and_run(tmp_path: Path) -> None:
    sys.path.insert(0, str(tmp_path))
    try:
        entry, helper = _write_pair(
            tmp_path, "def process(d):\n    return {'r': d.get('n', 0) * 2}\n"
        )
        plan = _lock(tmp_path, entry)
        ident = handle(_req(plan, entry, "identify"))
        assert ident["script_hash"]
        helper.write_text(
            "def process(d):\n    return {'r': 'SWAPPED'}\n", encoding="utf-8"
        )
        try:
            ran = handle(_req(plan, entry, "run", {"n": 5}))
        except ValueError as e:
            assert "dependency" in str(e) or "not pinned" in str(e)
            return
        assert ran.get("data") != {"r": "SWAPPED"}
        raise AssertionError(f"expected FAIL, got {ran}")
    finally:
        _SEALED.set(None)
        sys.modules.pop("helper", None)
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))


def test_worker_wrong_dep_hash_is_error(tmp_path: Path) -> None:
    sys.path.insert(0, str(tmp_path))
    try:
        entry, _helper = _write_pair(
            tmp_path, "def process(d):\n    return {'r': d.get('n', 0)}\n"
        )
        plan = _lock(tmp_path, entry)
        plan["module_hashes"]["dep:helper.py"] = "0" * 64
        plan["dependency_hashes"]["helper.py"] = "0" * 64
        try:
            handle(_req(plan, entry, "identify"))
        except ValueError as e:
            assert "dependency" in str(e)
            return
        raise AssertionError("wrong dep:* hash must not identify")
    finally:
        _SEALED.set(None)
        sys.modules.pop("helper", None)
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))


def test_worker_live_import_without_hash_is_error(tmp_path: Path) -> None:
    sys.path.insert(0, str(tmp_path))
    try:
        entry, _helper = _write_pair(
            tmp_path, "def process(d):\n    return {'r': d.get('n', 0)}\n"
        )
        plan = _lock(tmp_path, entry)
        req = _req(plan, entry, "identify")
        req.pop("dependency_hashes", None)
        req["module_hashes"] = {
            k: v for k, v in req["module_hashes"].items() if not k.startswith("dep:")
        }
        try:
            handle(req)
        except ValueError as e:
            assert "not pinned" in str(e) or "dependency" in str(e)
            return
        raise AssertionError("live local import without hash must be a worker error")
    finally:
        _SEALED.set(None)
        sys.modules.pop("helper", None)
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))


def test_rust_swapped_helper_is_fail_not_pass(tmp_path: Path) -> None:
    from tests.integration.test_rust_judge import rust_judge

    entry, helper = _write_pair(
        tmp_path, "def process(d):\n    return {'r': d.get('n', 0) * 2}\n"
    )
    plan = _lock(tmp_path, entry)
    helper.write_text(
        "def process(d):\n    return {'r': 'SWAPPED'}\n", encoding="utf-8"
    )
    rust = rust_judge(
        {
            "module_hashes": dict(plan["module_hashes"]),
            "dependency_hashes": dict(plan.get("dependency_hashes") or {}),
            "worker_hash": source_hash(),
            "runtime_hashes": runtime_hashes(),
            "source_hash": plan["source_hash"],
            "worker": {
                "python": sys.executable,
                "script": str(entry),
                "input": {"n": 5},
                "cwd": str(tmp_path),
            },
        }
    )
    assert rust["status"] != "PASS"
    assert rust["status"] == "FAIL"
    assert rust.get("data") != {"r": "SWAPPED"}
