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
