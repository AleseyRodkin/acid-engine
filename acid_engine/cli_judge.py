"""Pinned CLI admit. The only CLI path that can return PASS.

No argparse. Help text lives in cli.py, which is not in the pin.
Worker and CLI judge import from here, not from cli.py.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from acid_engine.level2.conformance import (
    ConformanceLevel,
    ConformanceResult,
    ConformanceStatus,
)
from acid_engine.level2.failure import FailureReason
from acid_engine.level3.pipeline import PipelineResult
from acid_engine.level3.script.module import ScriptModule


def load_script_from_file(path: str | Path) -> ScriptModule:
    """Load ScriptModule from .py (`script`) or .json blank. Markdown is not parsed.

    After source_hash_gate, this execs the pinned bytes, not a second disk read.
    """
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Script file not found: {source}")
    suffix = source.suffix.lower()
    if suffix == ".md":
        raise ValueError("markdown specs are not parsed")
    if suffix == ".json":
        from acid_engine.level2.blank_loader import load_script_blank
        return load_script_blank(source)
    if suffix != ".py":
        raise ValueError(f"Script must be a .py or .json file, got: {source}")
    from acid_engine.level2.local_deps import exec_source_module, read_source_bytes

    src = read_source_bytes(source)
    # unique name so repeated loads do not collide in sys.modules
    mod_name = f"acid_user_script_{source.resolve().stem}_{id(source)}"
    module = exec_source_module(source, src, mod_name)
    if not hasattr(module, "script"):
        raise ValueError(f"{source} does not define 'script'")
    script = module.script
    if not isinstance(script, ScriptModule):
        raise TypeError(f"{source}: 'script' is {type(script)!r}, expected ScriptModule")
    return script


def source_hash_gate(script_path: str | Path, raw: Mapping[str, Any]) -> ConformanceResult | None:
    """Compare file bytes to the lock before exec. Missing pin is SKIPPED.

    On match, pins those bytes so the following load cannot see a later disk write.
    """
    from acid_engine.level2.local_deps import pin_source_bytes, snapshot_exec_target

    expected = raw.get("source_hash")
    if not expected:
        return ConformanceResult.skipped("source not pinned")
    path = Path(script_path)
    try:
        target, src, actual = snapshot_exec_target(path)
    except OSError as e:
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message="source file unreadable",
            failure=FailureReason(
                node_id=path.name,
                contract_id=path.name,
                property_name="source_hash",
                expected=str(expected),
                actual=str(e),
            ),
        )
    if actual != str(expected):
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message="source_hash mismatch",
            failure=FailureReason(
                node_id=path.name,
                contract_id=path.name,
                property_name="source_hash",
                expected=str(expected),
                actual=actual,
            ),
        )
    pin_source_bytes(target, src)
    return None


def dummy_script(path: str | Path) -> ScriptModule:
    from acid_engine.level2.identity import ContractId, Version
    from acid_engine.level2.specification import Specification

    name = Path(path).stem
    return ScriptModule(
        contract_id=ContractId("source", name),
        version=Version(0, 0, 0),
        specification=Specification(),
        input_type="any",
        output_type="any",
        implementation=lambda x: x,
        name=name,
    )


@dataclass(frozen=True, slots=True)
class Admit:
    result: PipelineResult
    script: ScriptModule
    plan: Any = None
    iface: Any = None
    toolchain: Any = None
    runtime_pinned: bool = False


def admit_judge(
    script_path: str | Path,
    plan_raw: Mapping[str, Any],
    input_val: Any,
    *,
    iface: Any,
    plan: Any,
    script: ScriptModule | None = None,
) -> Admit:
    """Source-hash gate, load, runtime pin, judge_script.

    The only CLI entry that may return PASS.
    """
    from acid_engine.judge import judge_script
    from acid_engine.level2.implementation_canon import live_canon_kind
    from acid_engine.worker import verify_runtime_pin

    path = Path(script_path)
    gate = source_hash_gate(path, plan_raw)
    if gate is not None:
        return Admit(
            result=PipelineResult(conformance=gate),
            script=script if script is not None else dummy_script(path),
            plan=plan,
            iface=iface,
            toolchain=plan_raw,
        )
    if script is None:
        script = load_script_from_file(path)
    pin = verify_runtime_pin(
        plan_raw, live_canon_kind=live_canon_kind(script.implementation)
    )
    if pin is not None:
        return Admit(
            result=PipelineResult(conformance=pin),
            script=script,
            plan=plan,
            iface=iface,
            toolchain=plan_raw,
        )
    result = judge_script(
        script, input_val, plan=plan, iface=iface, toolchain=plan_raw
    )
    return Admit(
        result=result,
        script=script,
        plan=plan,
        iface=iface,
        toolchain=plan_raw,
        runtime_pinned=True,
    )


def admit_bound(
    script: ScriptModule,
    input_val: Any,
    *,
    iface: Any,
    plan: Any,
    toolchain: Mapping[str, Any],
) -> PipelineResult:
    """Judge branch of `locks --judge`. PASS only through judge_script."""
    from acid_engine.judge import judge_script

    return judge_script(
        script, input_val, plan=plan, iface=iface, toolchain=toolchain
    )


def _parse_input(raw: str | None, default: Any = 3) -> Any:
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def cmd_judge(args: Any) -> None:
    """The only CLI path that may print PASS. Argparse help lives in cli.py."""
    import sys

    from acid_engine.judge import SELF_LOCK_SKIP
    from acid_engine.level2.conformance import explain_block, explain_result
    from acid_engine.level3.script.runner import load_script_lock

    if not getattr(args, "script", None):
        print("ERROR: lock not passed — judge requires --script")
        sys.exit(1)
    input_val = _parse_input(getattr(args, "input", None), default=3)
    script_path = Path(args.script)
    if not getattr(args, "plan", None):
        if not script_path.exists():
            print(f"ERROR: Failed to load script: Script file not found: {args.script}")
            sys.exit(1)
        dummy = dummy_script(script_path)
        skipped = ConformanceResult.skipped(SELF_LOCK_SKIP)
        result = PipelineResult(conformance=skipped)
        print(explain_result(result.conformance))
        _write_judge_receipt(args, dummy, input_val, result, plan=None, toolchain=None)
        sys.exit(1)
    try:
        raw = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        iface, plan = load_script_lock(raw)
    except Exception as e:
        print(f"ERROR: Failed to load plan: {e}")
        sys.exit(1)
    admit = admit_judge(args.script, raw, input_val, iface=iface, plan=plan)
    result = admit.result
    if admit.runtime_pinned:
        print("runtime: pinned")
    print(explain_block(result.conformance))
    if admit.runtime_pinned:
        print(f"output: {result.data}")
        print(f"interface_contract_hash: {plan.interface_contract_hash}")
        print(f"plan_content_hash: {plan.content_hash}")
    _write_judge_receipt(
        args, admit.script, input_val, result, plan=plan, toolchain=raw
    )
    if not result.ok:
        sys.exit(1)


def _write_judge_receipt(
    args: Any,
    script: Any,
    input_val: Any,
    result: Any,
    plan: Any,
    toolchain: Any | None,
) -> None:
    path = getattr(args, "receipt", None)
    if not path:
        return
    from acid_engine.receipt import build_receipt, write_receipt

    ctx: dict[str, str] = {}
    agent = getattr(args, "agent", None)
    repo = getattr(args, "repository", None)
    if isinstance(agent, str) and agent.strip():
        ctx["agent"] = agent.strip()
    if isinstance(repo, str) and repo.strip():
        ctx["repository"] = repo.strip()
    payload = build_receipt(
        script,
        input_val,
        result,
        plan=plan,
        toolchain=toolchain,
        context=ctx or None,
    )
    write_receipt(path, payload)
    print(f"receipt: {path}")
