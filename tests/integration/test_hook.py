"""PreToolUse: deny on swapped hash. Pre is not PASS. No MCP."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "examples" / "hooks" / "pre_tool_use.py"


def _run(event: dict) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS" not in proc.stdout
    return json.loads(proc.stdout)


def test_hook_bound_is_allow_not_pass():
    out = _run({"hook_event_name": "PreToolUse", "tool_name": "clean_text", "tool_input": {}})
    decision = out["hookSpecificOutput"]["permissionDecision"]
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert decision == "allow"
    assert reason == "bound"
    assert "PASS" not in json.dumps(out)


def test_hook_swapped_plan_is_deny():
    import tempfile

    src_plan = ROOT / "examples" / "tools" / "clean_text.plan.json"
    raw = json.loads(src_plan.read_text(encoding="utf-8"))
    raw["module_hashes"]["clean_text"] = "0" * 64
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "clean_text.plan.json"
        plan_path.write_text(json.dumps(raw), encoding="utf-8")
        index = {
            "schema": "acid.locks.v1",
            "entries": [
                {
                    "id": "clean_text",
                    "script": "examples/tools/clean_text.json",
                    "plan": str(plan_path),
                    "input": {"text": "x"},
                }
            ],
        }
        index_path = Path(tmp) / "index.json"
        index_path.write_text(json.dumps(index), encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["ACID_LOCKS_INDEX"] = str(index_path)
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"tool_name": "clean_text", "tool_input": {}}),
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
        )
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "mismatch" in out["hookSpecificOutput"]["permissionDecisionReason"]
        assert "PASS" not in proc.stdout


def test_hook_unknown_tool_is_deny():
    out = _run({"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "not a locked tool"


def test_hook_same_stem_foreign_file_is_deny(tmp_path: Path) -> None:
    twin = tmp_path / "clean_text.py"
    twin.write_text("def clean_text(data): return data\n", encoding="utf-8")
    out = _run({"tool_name": "pwn", "tool_input": {"script": str(twin)}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "not a locked tool"


def test_hook_stolen_id_with_foreign_path_is_deny(tmp_path: Path) -> None:
    twin = tmp_path / "clean_text.py"
    twin.write_text("def clean_text(data): return data\n", encoding="utf-8")
    out = _run({"tool_name": "clean_text", "tool_input": {"script": str(twin)}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "not a locked tool"


def test_hook_import_side_effect_does_not_run(tmp_path: Path) -> None:
    honest = (ROOT / "examples" / "tools" / "clean_text.py").read_text(encoding="utf-8")
    plan = (ROOT / "examples" / "tools" / "clean_text.plan.json").read_text(encoding="utf-8")
    blank = (ROOT / "examples" / "tools" / "clean_text.json").read_text(encoding="utf-8")
    marker = tmp_path / "pwned"
    (tmp_path / "clean_text.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('pwn')\n" + honest,
        encoding="utf-8",
    )
    (tmp_path / "clean_text.json").write_text(blank, encoding="utf-8")
    (tmp_path / "clean_text.plan.json").write_text(plan, encoding="utf-8")
    index = {
        "schema": "acid.locks.v1",
        "entries": [
            {
                "id": "clean_text",
                "script": str(tmp_path / "clean_text.json"),
                "plan": str(tmp_path / "clean_text.plan.json"),
                "input": {"text": "x"},
            }
        ],
    }
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["ACID_LOCKS_INDEX"] = str(index_path)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "clean_text", "tool_input": {}}),
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "source" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert not marker.exists()
    assert "PASS" not in proc.stdout


def test_hook_is_not_mcp_and_not_judge():
    text = HOOK.read_text(encoding="utf-8")
    assert "judge_script" not in text
    assert "mcp" not in text.lower()
    assert "PASS" not in text or "not PASS" in text or "must not emit PASS" in text
    assert (ROOT / "examples" / "hooks" / "claude_settings.fragment.json").is_file()
    mcp = list((ROOT / "examples" / "hooks").glob("*mcp*"))
    assert mcp == []
