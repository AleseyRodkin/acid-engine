"""Swap compute_amount body against frozen plan → FAIL source_hash. Repo file stays clean."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "examples" / "tools" / "compute_amount.py"
PLAN = ROOT / "examples" / "tools" / "compute_amount.plan.json"
INCOMING = '{"cents": 1999, "qty": 2}'


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-m", "acid_engine", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )


def test_honest_compute_amount_pass_receipt(tmp_path: Path):
    rec = tmp_path / "amount-ok.receipt.json"
    proc = _cli(
        "judge",
        "--script",
        str(SRC),
        "--plan",
        str(PLAN),
        "--input",
        INCOMING,
        "--receipt",
        str(rec),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS" in proc.stdout
    payload = json.loads(rec.read_text(encoding="utf-8"))
    assert payload["verdict"]["status"] == "PASS"
    assert payload["output"] == {"cents": 3998}
    assert "proven_pure" not in json.dumps(payload)


def test_tampered_compute_amount_fails_source_hash(tmp_path: Path):
    original = SRC.read_text(encoding="utf-8")
    assert "cents * qty" in original
    assert "cents * qty + 1" not in original
    bad = original.replace("cents * qty", "cents * qty + 1", 1)
    assert bad != original
    copy = tmp_path / "compute_amount.py"
    copy.write_text(bad, encoding="utf-8")
    rec = tmp_path / "amount-bad.receipt.json"
    proc = _cli(
        "judge",
        "--script",
        str(copy),
        "--plan",
        str(PLAN),
        "--input",
        INCOMING,
        "--receipt",
        str(rec),
    )
    assert proc.returncode != 0
    assert "source_hash" in proc.stdout
    assert "was not imported" in proc.stdout
    assert "PASS" not in proc.stdout
    payload = json.loads(rec.read_text(encoding="utf-8"))
    assert payload["verdict"]["status"] == "FAIL"
    assert payload["verdict"].get("property") == "source_hash"
    assert payload.get("output") in (None, {})
    assert SRC.read_text(encoding="utf-8") == original
