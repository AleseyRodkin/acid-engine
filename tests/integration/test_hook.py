"""PreToolUse: deny on swapped hash. Pre is not PASS. No MCP.

Foreign repo uses ACID_REPO_ROOT / ACID_LOCKS_INDEX. Package comes from pip
(PYTHONPATH in tests). Hook is not in the pin.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from acid_engine.worker import RUNTIME_PIN_PATHS

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "examples" / "hooks" / "pre_tool_use.py"
PRODUCT_IDS = (
    "n_plus_one",
    "clean_text",
    "normalize_id",
    "compute_amount",
    "route_ticket",
    "emit_forecast_card",
)


def _run(event: dict, *, cwd: Path | None = None, extra_env: dict[str, str] | None = None) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        cwd=str(cwd or ROOT),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS" not in proc.stdout
    return json.loads(proc.stdout)


def _foreign_tree(tmp_path: Path) -> Path:
    tools = tmp_path / "tools"
    locks = tmp_path / "locks"
    tools.mkdir()
    locks.mkdir()
    for name in ("clean_text.json", "clean_text.plan.json"):
        shutil.copy(ROOT / "examples" / "tools" / name, tools / name)
    index = {
        "schema": "acid.locks.v1",
        "entries": [
            {
                "id": "clean_text",
                "script": "tools/clean_text.json",
                "plan": "tools/clean_text.plan.json",
                "input": {"text": "x"},
            }
        ],
    }
    (locks / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return tmp_path


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
        out = _run(
            {"tool_name": "clean_text", "tool_input": {}},
            extra_env={"ACID_LOCKS_INDEX": str(index_path)},
        )
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "mismatch" in out["hookSpecificOutput"]["permissionDecisionReason"]
        assert "PASS" not in json.dumps(out)


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
    out = _run(
        {"tool_name": "clean_text", "tool_input": {}},
        extra_env={"ACID_LOCKS_INDEX": str(index_path)},
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "source" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert not marker.exists()
    assert "PASS" not in json.dumps(out)


def test_hook_foreign_repo_unknown_is_deny(tmp_path: Path) -> None:
    tree = _foreign_tree(tmp_path)
    out = _run(
        {"tool_name": "Bash", "tool_input": {"command": "echo hi"}},
        cwd=tree,
        extra_env={
            "ACID_REPO_ROOT": str(tree),
            "ACID_LOCKS_INDEX": str(tree / "locks" / "index.json"),
        },
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "not a locked tool"
    assert "PASS" not in json.dumps(out)


def test_hook_foreign_repo_tamper_is_deny(tmp_path: Path) -> None:
    tree = _foreign_tree(tmp_path)
    body = tree / "tools" / "clean_text.json"
    body.write_text(body.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    out = _run(
        {"tool_name": "clean_text", "tool_input": {}},
        cwd=tree,
        extra_env={
            "ACID_REPO_ROOT": str(tree),
            "ACID_LOCKS_INDEX": str(tree / "locks" / "index.json"),
        },
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "PASS" not in json.dumps(out)


def test_hook_is_not_mcp_and_not_judge():
    text = HOOK.read_text(encoding="utf-8")
    assert "judge_script" not in text
    assert "mcp" not in text.lower()
    assert "sys.path.insert" not in text
    assert "parents[2]" not in text
    assert "PASS" not in text or "not PASS" in text or "must not emit PASS" in text or "Pre ≠ PASS" in text
    fragment = ROOT / "examples" / "hooks" / "claude_settings.fragment.json"
    assert fragment.is_file()
    mcp = list((ROOT / "examples" / "hooks").glob("*mcp*"))
    assert mcp == []


def test_fragment_matcher_is_placeholder_not_product_ids():
    fragment = (ROOT / "examples" / "hooks" / "claude_settings.fragment.json").read_text(
        encoding="utf-8"
    )
    assert "YOUR_TOOL_ID" in fragment
    for ident in PRODUCT_IDS:
        assert ident not in fragment
    product = (
        ROOT / "examples" / "hooks" / "claude_settings.product.fragment.json"
    ).read_text(encoding="utf-8")
    for ident in PRODUCT_IDS:
        assert ident in product


def test_hook_not_in_runtime_pin():
    assert "examples/hooks/pre_tool_use.py" not in RUNTIME_PIN_PATHS
    assert len(RUNTIME_PIN_PATHS) == 8


def test_hook_index_pin_mismatch_is_deny(tmp_path: Path) -> None:
    from acid_engine.worker import runtime_hashes, source_hash

    tree = _foreign_tree(tmp_path)
    index_path = tree / "locks" / "index.json"
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    hashes = dict(runtime_hashes())
    hashes["acid_engine/action_driver.py"] = "0" * 64
    raw["worker_hash"] = source_hash()
    raw["runtime_hashes"] = hashes
    index_path.write_text(json.dumps(raw), encoding="utf-8")
    out = _run(
        {"tool_name": "clean_text", "tool_input": {}},
        cwd=tree,
        extra_env={
            "ACID_REPO_ROOT": str(tree),
            "ACID_LOCKS_INDEX": str(index_path),
        },
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "runtime_hash" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "PASS" not in json.dumps(out)


def test_hook_no_pin_is_bind_only_not_pass(tmp_path: Path) -> None:
    tree = _foreign_tree(tmp_path)
    shutil.copy(ROOT / "examples" / "tools" / "clean_text.py", tree / "tools" / "clean_text.py")
    index_path = tree / "locks" / "index.json"
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    assert "worker_hash" not in raw
    out = _run(
        {"tool_name": "clean_text", "tool_input": {}},
        cwd=tree,
        extra_env={
            "ACID_REPO_ROOT": str(tree),
            "ACID_LOCKS_INDEX": str(index_path),
        },
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "bound"
    assert "PASS" not in json.dumps(out)
