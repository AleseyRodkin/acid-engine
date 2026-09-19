"""Claude Code PreToolUse: bind plan.lock. Deny on hash mismatch. Not PASS.

If this hook runs, the tool must be in the index. Unknown → deny
(not enough facts is not allow). The settings matcher is how Bash / Read
never reach this script — this is not a policy gate for the whole agent.

Lookup is exact entry id or a resolved script path. Basename is not identity.
A tool_input path that exists must be the locked file, not a namesake.

Install the package (`pip install acid-judge`). Point the hook at the
consumer repo with ACID_REPO_ROOT / ACID_LOCKS_INDEX. Pre ≠ PASS.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from acid_engine.cli_judge import load_script_from_file, source_hash_gate
from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level3.script.resolve import materialize_script
from acid_engine.level3.script.runner import bind_script_to_plan, load_script_lock


def repo_root() -> Path:
    raw = os.environ.get("ACID_REPO_ROOT", "").strip()
    if raw:
        return Path(raw)
    return Path.cwd()


def index_path() -> Path:
    raw = os.environ.get("ACID_LOCKS_INDEX", "").strip()
    if raw:
        return Path(raw)
    return repo_root() / "locks" / "index.json"


def load_entries() -> list[dict[str, Any]]:
    raw = json.loads(index_path().read_text(encoding="utf-8"))
    entries = raw.get("entries") or []
    return [e for e in entries if isinstance(e, dict)]


def _existing_file(p: str) -> Path | None:
    if not p:
        return None
    loc = Path(p)
    if not loc.is_absolute():
        loc = repo_root() / loc
    try:
        if loc.is_file():
            return loc.resolve()
    except OSError:
        return None
    return None


def lookup(event: dict[str, Any]) -> dict[str, Any] | None:
    """Exact id or resolved script path. Stem / suffix is not a match."""
    name = str(event.get("tool_name") or "")
    raw_input = event.get("tool_input")
    payload: dict[str, Any] = raw_input if isinstance(raw_input, dict) else {}
    ident = str(payload.get("id") or payload.get("script") or name)
    event_script = str(payload.get("script") or payload.get("file") or "")
    named_path = bool(event_script)
    event_path = _existing_file(event_script) if named_path else None

    for entry in load_entries():
        eid = str(entry.get("id") or "")
        script = str(entry.get("script") or "")
        locked = _existing_file(script)
        if named_path:
            if event_path is None or locked is None:
                continue
            if event_path == locked:
                return entry
            continue
        if eid and (ident == eid or name == eid):
            return entry
        if script and ident == script:
            return entry
    return None


def bind_entry(entry: dict[str, Any]) -> str:
    """Return allow/deny reason. Never PASS."""
    plan_path = entry.get("plan")
    script_path = entry.get("script")
    if not plan_path or not script_path:
        return "deny: lock not passed"
    root = repo_root()
    script_file = Path(str(script_path))
    if not script_file.is_absolute():
        script_file = root / script_file
    plan_file = Path(str(plan_path))
    if not plan_file.is_absolute():
        plan_file = root / plan_file
    try:
        raw = json.loads(plan_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return f"deny: {e}"
    gate = source_hash_gate(script_file, raw)
    if gate is not None:
        return f"deny: {gate.message}"
    script = materialize_script(load_script_from_file(script_file))
    _iface, plan = load_script_lock(raw)
    result = bind_script_to_plan(plan, script)
    if result is None:
        return "allow: bound"
    if result.status == ConformanceStatus.FAIL:
        return f"deny: {result.message}"
    return f"deny: {result.message}"


def decision_payload(permission: str, reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission,
            "permissionDecisionReason": reason,
        }
    }


def handle(event: dict[str, Any]) -> dict[str, Any]:
    entry = lookup(event)
    if entry is None:
        return decision_payload("deny", "not a locked tool")
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
