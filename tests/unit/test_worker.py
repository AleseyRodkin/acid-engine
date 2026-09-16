"""Worker runs a body and does not emit a verdict."""
from __future__ import annotations

import json
from pathlib import Path

from acid_engine.level2.local_deps import snapshot_exec_target
from acid_engine.worker import handle

ROOT = Path(__file__).resolve().parents[2]
BONES = ROOT / "examples" / "bones" / "n_plus_one.json"
_, _, BONES_HASH = snapshot_exec_target(BONES)


def test_identify_has_hash_not_verdict():
    out = handle({"op": "identify", "script": str(BONES), "source_hash": BONES_HASH})
    assert out["script_name"] == "n_plus_one"
    assert len(out["script_hash"]) == 64
    assert out["output_type"] == "dict"
    assert "status" not in out
    assert "PASS" not in json.dumps(out)


def test_run_returns_observation_not_pass():
    out = handle(
        {"op": "run", "script": str(BONES), "input": {"n": 3}, "source_hash": BONES_HASH}
    )
    assert out["data"] == {"n": 4}
    assert out["observation"]["status"] == "completed"
    assert out["effects"] == []
    dumped = json.dumps(out)
    assert "PASS" not in dumped
    assert "FAIL" not in dumped
    assert "SKIPPED" not in dumped


def test_unknown_op_is_error():
    try:
        handle({"op": "judge", "script": str(BONES), "source_hash": BONES_HASH})
        assert False
    except ValueError as e:
        assert "unknown worker op" in str(e)


def test_worker_without_source_hash_does_not_import(tmp_path: Path) -> None:
    marker = tmp_path / "pwned"
    tool = tmp_path / "inc.py"
    tool.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('pwn')\n"
        "script = None\n",
        encoding="utf-8",
    )
    try:
        handle({"op": "identify", "script": str(tool)})
        raise AssertionError("expected source not pinned")
    except ValueError as e:
        assert "source not pinned" in str(e)
    assert not marker.exists()
