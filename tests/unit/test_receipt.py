"""Receipt: PASS bones, foreign plan FAIL, CLI without plan SKIPPED, live serialize."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from acid_engine.cli import load_script_from_file
from acid_engine.judge import judge_script
from acid_engine.level2.serialization import canonical_serialize
from acid_engine.level3.script.resolve import materialize_script
from acid_engine.level3.script.runner import load_script_lock
from acid_engine.receipt import SCHEMA, build_receipt, write_receipt

ROOT = Path(__file__).resolve().parents[2]
BONES = ROOT / "examples" / "bones"
SCRIPT = BONES / "n_plus_one.json"
PLAN = BONES / "n_plus_one.plan.json"


def _cli(*args: str, receipt: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    cmd = [sys.executable, "-m", "acid_engine", "judge", *args]
    if receipt:
        cmd.extend(["--receipt", receipt])
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))


def test_receipt_bones_pass():
    script = materialize_script(load_script_from_file(SCRIPT))
    raw = json.loads(PLAN.read_text(encoding="utf-8"))
    iface, plan = load_script_lock(raw)
    result = judge_script(script, {"n": 3}, plan=plan, iface=iface, toolchain=raw)
    assert result.ok
    rec = build_receipt(
        script, {"n": 3}, result, plan=plan, toolchain=raw, timestamp="2026-08-31T00:00:00Z"
    )
    assert rec["schema"] == SCHEMA
    assert "context" not in rec
    assert rec["script_name"] == "n_plus_one"
    assert rec["contract_id"] == "bones/n_plus_one"
    assert rec["body_hash"] == script.content_hash
    assert rec["plan_hash"] == plan.content_hash
    assert rec["output"] == {"n": 4}
    assert rec["verdict"]["status"] == "PASS"
    assert rec["verdict"]["property"] is None
    assert rec["observation"]["status"] == "completed"
    assert rec["toolchain"]["worker_hash"] == raw["toolchain"]["worker_hash"]
    assert rec["toolchain"]["runtime_hashes"] == raw["toolchain"]["runtime_hashes"]
    assert rec["toolchain"]["canon"] == "python.ast.v1"
    assert rec["evidence"]["missing"] == []
    text = canonical_serialize(rec)
    assert "proven_pure" not in text
    assert "callable" not in text
    with_ctx = build_receipt(
        script,
        {"n": 3},
        result,
        plan=plan,
        toolchain=raw,
        timestamp="2026-08-31T00:00:00Z",
        context={"agent": "claude-code", "repository": "acme/pay", "secret": "nope"},
    )
    assert with_ctx["context"] == {"agent": "claude-code", "repository": "acme/pay"}
    assert "secret" not in with_ctx["context"]


def test_receipt_swapped_plan_fail_module_hash():
    script = materialize_script(load_script_from_file(SCRIPT))
    raw = json.loads(PLAN.read_text(encoding="utf-8"))
    raw["module_hashes"]["n_plus_one"] = "0" * 64
    iface, plan = load_script_lock(raw)
    result = judge_script(script, {"n": 3}, plan=plan, iface=iface, toolchain=raw)
    assert not result.ok
    rec = build_receipt(script, {"n": 3}, result, plan=plan)
    assert rec["verdict"]["status"] == "FAIL"
    assert rec["verdict"]["property"] == "module_hash"
    assert rec["evidence"]["missing"] == []
    assert rec["observation"] is None
    assert rec["output"] is None


def test_cli_receipt_without_plan_is_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "receipt.json")
        proc = _cli("--script", str(SCRIPT), "--input", '{"n": 3}', receipt=out)
        assert proc.returncode != 0
        assert "SKIPPED" in proc.stdout
        rec = json.loads(Path(out).read_text(encoding="utf-8"))
        assert rec["schema"] == SCHEMA
        assert rec["verdict"]["status"] == "SKIPPED"
        assert rec["plan_hash"] is None
        assert "lock" in rec["evidence"]["missing"]
        assert "proven_pure" not in json.dumps(rec)


def test_cli_receipt_bones_pass_serializes():
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "receipt.json")
        proc = _cli(
            "--script",
            str(SCRIPT),
            "--plan",
            str(PLAN),
            "--input",
            '{"n": 3}',
            receipt=out,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        rec = json.loads(Path(out).read_text(encoding="utf-8"))
        canonical_serialize(rec)
        assert rec["verdict"]["status"] == "PASS"
        assert rec["output"] == {"n": 4}
        write_receipt(Path(tmp) / "copy.json", rec)
        assert "proven_pure" not in Path(out).read_text(encoding="utf-8")


def test_cli_receipt_agent_context(tmp_path: Path):
    out = tmp_path / "receipt.json"
    proc = _cli(
        "--script",
        str(SCRIPT),
        "--plan",
        str(PLAN),
        "--input",
        '{"n": 3}',
        "--agent",
        "claude-code",
        "--repository",
        "acme/pay",
        receipt=str(out),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["context"] == {"agent": "claude-code", "repository": "acme/pay"}
    assert rec["verdict"]["status"] == "PASS"
