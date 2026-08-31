"""Claude Code PreToolUse: bind plan.lock. Deny on hash mismatch. Not PASS."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acid_engine.cli import load_script_from_file
from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level3.script.resolve import materialize_script
from acid_engine.level3.script.runner import bind_script_to_plan, load_script_lock

ROOT = Path(__file__).resolve().parents[2]
INDEX = Path(os.environ.get("ACID_LOCKS_INDEX") or ROOT / "locks" / "index.json")


def load_entries() -> list[dict]:
    raw = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = raw.get("entries") or []
    return [e for e in entries if isinstance(e, dict)]


def lookup(event: dict) -> dict | None:
    name = str(event.get("tool_name") or "")
    payload = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    ident = str(payload.get("id") or payload.get("script") or name)
    for entry in load_entries():
        if entry.get("id") == ident:
            return entry
        script = str(entry.get("script") or "")
        if script and ident.endswith(script):
            return entry
        if Path(ident).name and Path(script).stem == Path(ident).stem:
            return entry
    return None


def bind_entry(entry: dict) -> str:
    """Return allow/deny reason. Never PASS."""
    plan_path = entry.get("plan")
    script_path = entry.get("script")
    if not plan_path or not script_path:
        return "deny: lock not passed"
    script = materialize_script(load_script_from_file(ROOT / str(script_path)))
    raw = json.loads((ROOT / str(plan_path)).read_text(encoding="utf-8"))
    _iface, plan = load_script_lock(raw)
    result = bind_script_to_plan(plan, script)
    if result is None:
        return "allow: bound"
    if result.status == ConformanceStatus.FAIL:
        return f"deny: {result.message}"
    return f"deny: {result.message}"


def decision_payload(permission: str, reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission,
            "permissionDecisionReason": reason,
        }
    }


def handle(event: dict) -> dict:
    entry = lookup(event)
    if entry is None:
        return decision_payload("allow", "not a locked tool")
    text = bind_entry(entry)
    permission, _, reason = text.partition(": ")
    return decision_payload(permission, reason)


def main() -> None:
    raw = sys.stdin.read()
    event = json.loads(raw) if raw.strip() else {}
    if not isinstance(event, dict):
        event = {}
    out = handle(event)
    dumped = json.dumps(out, ensure_ascii=False)
    if "PASS" in dumped:
        raise SystemExit("pre hook must not emit PASS")
    sys.stdout.write(dumped + "\n")


if __name__ == "__main__":
    main()
