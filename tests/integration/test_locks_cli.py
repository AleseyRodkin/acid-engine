"""CLI locks --index: live body vs plan.lock. Does not run, not PASS."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "locks" / "index.json"


def _cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-m", "acid_engine", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd or ROOT),
    )


def test_locks_index_all_bound():
    proc = _cli("locks", "--index", str(INDEX))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "[BOUND]" in proc.stdout
    assert "n_plus_one" in proc.stdout
    assert "clean_text" in proc.stdout
    assert "PASS" not in proc.stdout
    assert "Tools checked:" in proc.stdout
    assert "Bind only" in proc.stdout


def test_locks_judge_pass_writes_receipt(tmp_path: Path):
    proc = _cli("locks", "--index", str(INDEX), "--judge", "--receipts", str(tmp_path))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "[BOUND]" in proc.stdout
    assert "PASS" in proc.stdout
    assert "Execution integrity: PASS" in proc.stdout
    rec = tmp_path / "n_plus_one.json"
    assert rec.is_file()
    payload = json.loads(rec.read_text(encoding="utf-8"))
    assert payload["verdict"]["status"] == "PASS"
    assert "proven_pure" not in json.dumps(payload)
    assert "toolchain" in payload


def test_locks_swapped_hash_fails():
    raw = json.loads(INDEX.read_text(encoding="utf-8"))
    plan_src = ROOT / "examples" / "tools" / "clean_text.plan.json"
    plan = json.loads(plan_src.read_text(encoding="utf-8"))
    plan["module_hashes"]["clean_text"] = "0" * 64
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bad_plan = tmp_path / "clean_text.plan.json"
        bad_plan.write_text(json.dumps(plan), encoding="utf-8")
        raw["entries"] = [
            {
                "id": "clean_text",
                "script": str(ROOT / "examples" / "tools" / "clean_text.json"),
                "plan": str(bad_plan),
                "input": {"text": "x"},
            }
        ]
        idx = tmp_path / "index.json"
        idx.write_text(json.dumps(raw), encoding="utf-8")
        proc = _cli("locks", "--index", str(idx), cwd=tmp_path)
        assert proc.returncode != 0
        assert "FAIL" in proc.stdout
        assert "module hash" in proc.stdout.lower() or "mismatch" in proc.stdout.lower()
        assert "PASS" not in proc.stdout


def test_locks_judge_keeps_plan_snapshot(tmp_path: Path, monkeypatch):
    """Changing the plan file after the first read must not re-bind locks --judge."""
    from argparse import Namespace
    from contextlib import redirect_stdout
    from io import StringIO

    from acid_engine.cli import cmd_locks
    from acid_engine.worker import runtime_hashes, source_hash

    entry = tmp_path / "entry.py"
    entry.write_text(
        """
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def entry(data):
    return {"r": data.get("n", 0) + 1}


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
    plan = tmp_path / "entry.plan.json"
    lock = _cli("lock", "--script", str(entry), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    index = tmp_path / "index.json"
    index.write_text(
        json.dumps(
            {
                "schema": "acid.locks.v1",
                "worker_hash": source_hash(),
                "runtime_hashes": runtime_hashes(),
                "entries": [
                    {
                        "id": "entry",
                        "script": str(entry),
                        "plan": str(plan),
                        "input": {"n": 1},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    orig = Path.read_text
    reads: list[int] = []

    def wrapped(self: Path, *args: object, **kwargs: object) -> str:
        text = orig(self, *args, **kwargs)
        if self.resolve() == plan.resolve():
            reads.append(1)
            if len(reads) == 1:
                raw = json.loads(text)
                tool = dict(raw.get("toolchain") or {})
                tool["worker_hash"] = "0" * 64
                raw["toolchain"] = tool
                Path.write_text(self, json.dumps(raw), encoding="utf-8")
        return text

    monkeypatch.setattr(Path, "read_text", wrapped)
    buf = StringIO()
    with redirect_stdout(buf):
        cmd_locks(
            Namespace(index=str(index), judge=True, receipts=str(tmp_path / "receipts"))
        )
    out = buf.getvalue()
    assert reads == [1]
    assert "PASS" in out
    assert "worker_hash mismatch" not in out
    rec = tmp_path / "receipts" / "entry.json"
    assert rec.is_file()
    payload = json.loads(rec.read_text(encoding="utf-8"))
    assert payload["verdict"]["status"] == "PASS"


def test_locks_missing_plan_fails():
    from acid_engine.worker import runtime_hashes, source_hash

    with tempfile.TemporaryDirectory() as tmp:
        idx = Path(tmp) / "index.json"
        idx.write_text(
            json.dumps(
                {
                    "schema": "acid.locks.v1",
                    "worker_hash": source_hash(),
                    "runtime_hashes": runtime_hashes(),
                    "entries": [{"id": "x", "script": "a.json"}],
                }
            ),
            encoding="utf-8",
        )
        proc = _cli("locks", "--index", str(idx), cwd=Path(tmp))
        assert proc.returncode != 0
        assert "lock not passed" in proc.stdout
