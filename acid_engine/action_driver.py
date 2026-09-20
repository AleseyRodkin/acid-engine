"""CI driver for the supervisor binary. In runtime_hashes (not a CLI verb)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from acid_engine.cli_judge import dummy_script
from acid_engine.level2.conformance import (
    ConformanceLevel,
    ConformanceResult,
    ConformanceStatus,
)
from acid_engine.level2.failure import FailureReason
from acid_engine.level3.pipeline import PipelineResult
from acid_engine.receipt import build_receipt, write_receipt


def _safe_id(ident: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in ident) or "entry"


def _conformance(status: str, message: str, property_name: str | None) -> ConformanceResult:
    if status == "PASS":
        return ConformanceResult(
            status=ConformanceStatus.PASS,
            level=ConformanceLevel.OPERATIONAL,
            message=message,
        )
    if status == "FAIL":
        failure = None
        if property_name:
            failure = FailureReason(
                node_id="",
                contract_id="",
                property_name=property_name,
                expected="",
                actual="",
                detail=message,
            )
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message=message,
            failure=failure,
        )
    return ConformanceResult.skipped(message)


def _write_receipt(
    receipts: Path,
    ident: str,
    script_path: str,
    input_data: Any,
    plan_raw: dict[str, Any],
    out: dict[str, Any],
) -> None:
    receipts.mkdir(parents=True, exist_ok=True)
    status = str(out.get("status") or "")
    message = str(out.get("message") or "")
    prop = out.get("property")
    property_name = str(prop) if isinstance(prop, str) and prop else None
    result = PipelineResult(
        conformance=_conformance(status, message, property_name),
        data=out.get("data"),
    )
    plan = None
    try:
        from acid_engine.level3.script.runner import load_script_lock

        _, plan = load_script_lock(plan_raw)
    except Exception:
        plan = None
    payload = build_receipt(
        dummy_script(script_path),
        input_data,
        result,
        plan=plan,
        toolchain=plan_raw,
    )
    write_receipt(receipts / f"{_safe_id(ident)}.json", payload)


def run(bin_path: Path, index_path: Path, receipts: Path) -> int:
    if not index_path.is_file():
        print(f"ERROR: index not found: {index_path}")
        return 2
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: index json: {e}")
        return 2
    if not isinstance(raw, dict):
        print("ERROR: index is not an object")
        return 2
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        print("ERROR: index has no entries")
        return 1
    failed = 0
    for i, item in enumerate(entries):
        if not isinstance(item, dict):
            print(f"ERROR: entry {i} is not an object")
            return 2
        ident = str(item.get("id") or i)
        script = item.get("script")
        plan_rel = item.get("plan")
        if not script or not plan_rel:
            print(f"[FAIL] {ident} script/plan required")
            failed += 1
            continue
        try:
            plan_raw = json.loads(Path(str(plan_rel)).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"[FAIL] {ident} plan: {e}")
            failed += 1
            continue
        if not isinstance(plan_raw, dict):
            print(f"[FAIL] {ident} plan is not an object")
            failed += 1
            continue
        toolchain_raw = plan_raw.get("toolchain")
        tool: dict[str, Any] = toolchain_raw if isinstance(toolchain_raw, dict) else {}
        req = {
            "module_hashes": plan_raw.get("module_hashes") or {},
            "dependency_hashes": plan_raw.get("dependency_hashes") or {},
            "worker_hash": tool.get("worker_hash") or raw.get("worker_hash"),
            "runtime_hashes": tool.get("runtime_hashes") or raw.get("runtime_hashes") or {},
            "source_hash": plan_raw.get("source_hash"),
            "worker": {
                "python": sys.executable,
                "script": str(script),
                "input": item.get("input"),
                "cwd": os.getcwd(),
            },
        }
        proc = subprocess.run(
            [str(bin_path)],
            input=json.dumps(req),
            capture_output=True,
            text=True,
        )
        try:
            out = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            print(f"[FAIL] {ident} supervisor json")
            sys.stderr.write(proc.stderr)
            failed += 1
            continue
        if not isinstance(out, dict):
            print(f"[FAIL] {ident} supervisor json")
            failed += 1
            continue
        status = str(out.get("status") or "")
        print(f"[{status}] {ident} {out.get('message', '')}")
        _write_receipt(receipts, ident, str(script), item.get("input"), plan_raw, out)
        if status != "PASS":
            failed += 1
    print("")
    print("Acid Judge")
    print(f"Tools checked: {len(entries)}")
    print(f"Failed: {failed}")
    print(f"Execution integrity: {'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="acid_engine.action_driver")
    parser.add_argument("--bin", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--receipts", default="receipts")
    args = parser.parse_args(argv)
    return run(Path(args.bin), Path(args.index), Path(args.receipts))


if __name__ == "__main__":
    sys.exit(main())
