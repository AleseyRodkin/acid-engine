"""Live files vs frozen plan.json. Inspection, not a verdict. Does not run the body."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NamedTuple

from acid_engine.level2.implementation_canon import canon_id_for
from acid_engine.level3.script.module import ScriptModule
from acid_engine.worker import RUNTIME_PIN_PATHS, runtime_hashes, source_hash


class DiffRow(NamedTuple):
    name: str
    approved: str
    live: str
    ok: bool


def _short(value: object) -> str:
    text = "" if value is None else str(value)
    if len(text) > 16:
        return text[:12] + "…"
    return text or "—"


def _tool(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = raw.get("toolchain")
    if isinstance(nested, Mapping):
        return nested
    return raw


def diff_lock(raw: Mapping[str, Any], script: ScriptModule) -> list[DiffRow]:
    from acid_engine.level2.implementation_canon import implementation_identity

    tool = _tool(raw)
    raw_hashes = raw.get("module_hashes")
    hashes: Mapping[str, Any] = raw_hashes if isinstance(raw_hashes, Mapping) else {}
    locked_body = str(hashes.get(script.name) or hashes.get(str(script.contract_id)) or "—")
    ident = implementation_identity(script.implementation)
    live_kind = "missing"
    if isinstance(ident, dict):
        live_kind = str(ident.get("kind") or "missing")
    live_canon = canon_id_for(live_kind)
    locked_kind = str(tool.get("canon_kind") or "—")
    locked_canon = str(tool.get("canon") or "—")
    live_worker = source_hash()
    locked_worker = str(tool.get("worker_hash") or "—")
    raw_rt = tool.get("runtime_hashes")
    pinned_rt: Mapping[str, Any] = raw_rt if isinstance(raw_rt, Mapping) else {}
    live_rt = runtime_hashes()
    rows = [
        DiffRow("body " + script.name, locked_body, script.content_hash, locked_body == script.content_hash),
        DiffRow("canon", locked_canon, live_canon, locked_canon == live_canon),
        DiffRow("canon_kind", locked_kind, live_kind, locked_kind == live_kind),
        DiffRow("worker.py", locked_worker, live_worker, locked_worker == live_worker),
    ]
    for rel in RUNTIME_PIN_PATHS:
        want = str(pinned_rt.get(rel) or "—")
        got = live_rt[rel]
        rows.append(DiffRow(rel, want, got, want == got))
    return rows


def format_diff(rows: list[DiffRow]) -> str:
    lines = ["APPROVED vs LIVE  (inspection, not a verdict)", ""]
    width = max(len(row.name) for row in rows)
    for row in rows:
        mark = "✓" if row.ok else "✗"
        lines.append(f"{row.name.ljust(width)}  {_short(row.approved)}  {_short(row.live)}  {mark}")
    lines.append("")
    drifted = [row.name for row in rows if not row.ok]
    if drifted:
        lines.append("DRIFT: " + ", ".join(drifted))
    else:
        lines.append("MATCH")
    lines.append("The body was not executed.")
    return "\n".join(lines)
