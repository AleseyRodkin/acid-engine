"""diff is inspection: MATCH/DRIFT, never PASS, never runs the body."""
from __future__ import annotations

import json
from pathlib import Path

from acid_engine.cli import load_script_from_file
from acid_engine.level2.conformance import (
    ConformanceLevel,
    ConformanceResult,
    ConformanceStatus,
    explain_block,
)
from acid_engine.level2.failure import FailureReason
from acid_engine.level3.script.resolve import materialize_script
from acid_engine.lock_diff import diff_lock, format_diff

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "examples" / "bones" / "n_plus_one.plan.json"
SCRIPT = ROOT / "examples" / "bones" / "n_plus_one.json"


def test_diff_committed_bones_matches():
    script = materialize_script(load_script_from_file(SCRIPT))
    raw = json.loads(PLAN.read_text(encoding="utf-8"))
    rows = diff_lock(raw, script)
    assert rows
    assert all(row.ok for row in rows)
    text = format_diff(rows)
    assert "MATCH" in text
    assert "PASS" not in text
    assert "The body was not executed." in text


def test_diff_poisoned_body_drifts():
    script = materialize_script(load_script_from_file(SCRIPT))
    raw = json.loads(PLAN.read_text(encoding="utf-8"))
    raw["module_hashes"][script.name] = "0" * 64
    rows = diff_lock(raw, script)
    assert any(not row.ok and row.name.startswith("body ") for row in rows)
    text = format_diff(rows)
    assert "DRIFT" in text
    assert "PASS" not in text


def test_explain_block_module_hash():
    result = ConformanceResult(
        status=ConformanceStatus.FAIL,
        level=ConformanceLevel.STRUCTURAL,
        message="x",
        failure=FailureReason(
            node_id="n",
            contract_id="c",
            property_name="module_hash",
            expected="a",
            actual="b",
        ),
    )
    text = explain_block(result)
    assert "Execution blocked" in text
    assert "module_hash" in text
    assert "was not executed" in text


def test_explain_block_runtime_hash_names_file():
    result = ConformanceResult(
        status=ConformanceStatus.FAIL,
        level=ConformanceLevel.STRUCTURAL,
        message="x",
        failure=FailureReason(
            node_id="runtime",
            contract_id="runtime",
            property_name="runtime_hash",
            expected="0" * 64,
            actual="1" * 64,
            detail="acid_engine/level2/implementation_canon.py",
        ),
    )
    text = explain_block(result)
    assert "implementation_canon.py" in text
    assert "runtime_hash" in text
    assert "was not executed" in text
