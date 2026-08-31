"""Worker runs a body and does not emit a verdict."""
from __future__ import annotations

import json
from pathlib import Path

from acid_engine.worker import handle

ROOT = Path(__file__).resolve().parents[2]
BONES = ROOT / "examples" / "bones" / "n_plus_one.json"


def test_identify_has_hash_not_verdict():
    out = handle({"op": "identify", "script": str(BONES)})
    assert out["script_name"] == "n_plus_one"
    assert len(out["script_hash"]) == 64
    assert out["output_type"] == "dict"
    assert "status" not in out
    assert "PASS" not in json.dumps(out)


def test_run_returns_observation_not_pass():
    out = handle({"op": "run", "script": str(BONES), "input": {"n": 3}})
    assert out["data"] == {"n": 4}
    assert out["observation"]["status"] == "completed"
    assert out["effects"] == []
    dumped = json.dumps(out)
    assert "PASS" not in dumped
    assert "FAIL" not in dumped
    assert "SKIPPED" not in dumped


def test_unknown_op_is_error():
    try:
        handle({"op": "judge", "script": str(BONES)})
        assert False
    except ValueError as e:
        assert "unknown worker op" in str(e)
