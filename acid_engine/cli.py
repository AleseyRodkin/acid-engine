"""CLI Acid Judge: lock, judge, receipt."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from acid_engine.level2.conformance import (
    ConformanceLevel,
    ConformanceResult,
    ConformanceStatus,
    check_conformance,
    explain_block,
    explain_result,
)
from acid_engine.level2.failure import FailureReason
from acid_engine.level2.specification import Policy
from acid_engine.level3.script.external_runner import run_external
from acid_engine.level3.script.modes import ExecutionMode
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


def parse_cli_input(raw: str | None, default: Any = 3) -> Any:
    """Parse --input: int, JSON (list/dict/...), else a string. Without --input → default."""
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


def cmd_init(args: argparse.Namespace) -> None:
    """Create a ScriptModule template (.py). Markdown specs are not written — they are not parsed."""
    target = Path(args.path or "script.py")
    if target.suffix == ".md":
        # old default was spec.md — do not write dead markdown
        target = Path("script.py")
        print("NOTE: markdown specs are not parsed; writing script.py instead")

    script_content = '''"""Demo script for AcidEngine."""
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level3.script.module import ScriptModule

script = ScriptModule(
    contract_id=ContractId(namespace="demo", name="my_script"),
    version=Version(0, 1, 0),
    specification=Specification(
        policy=Policy(pure=True, max_latency_ms=100),
    ),
    input_type="int",
    output_type="int",
    implementation=lambda x: x + 1,
    name="demo_script",
)
'''
    if args.script:
        target = Path(args.script)
    target.write_text(script_content, encoding="utf-8")
    print(f"Script created: {target}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Check an external command against a .py contract (`contract` variable)."""
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"ERROR: spec file not found: {spec_path}")
        sys.exit(1)
    if spec_path.suffix != ".py":
        print(
            "ERROR: markdown specs are not parsed. "
            "Pass a .py file that defines 'contract'."
        )
        sys.exit(1)

    try:
        from acid_engine.level2.loader import PythonLoader
        loader = PythonLoader()
        if loader.can_load(spec_path):
            iface = loader.load(spec_path)
        else:
            raise ValueError("Not a valid Python contract file")
    except Exception as e:
        print(f"ERROR: Failed to load contract: {e}")
        sys.exit(1)

    command = args.command if args.command else ["echo", "hello"]
    out_snap, obs, delta, state = run_external(
        command=command,
        contract_id=iface.contract_id,
        contract_hash=iface.content_hash,
        mode=ExecutionMode.NORMAL,
    )

    policy = Policy(
        max_latency_ms=iface.constraints.get("max_latency_ms"),
        pure=iface.constraints.get("pure", False),
    )

    result = check_conformance(
        required_output_type="dict",
        provided_data=out_snap.data,
        obs=obs,
        policy=policy,
        node_id=command[0],
        contract_id=str(iface.contract_id),
        semantic_rules=iface.constraints.get("semantic_rules"),
    )

    print(explain_result(result))
    if not result.ok:
        sys.exit(1)


def cmd_lock(args: argparse.Namespace) -> None:
    """Freeze the current body as plan.lock JSON. Not a verdict."""
    try:
        script = load_script_from_file(args.script)
    except Exception as e:
        print(f"ERROR: Failed to load script: {e}")
        sys.exit(1)
    from acid_engine.level2.local_deps import detect_dynamic_imports
    from acid_engine.level3.script.runner import dump_script_lock

    payload = dump_script_lock(script)
    out = Path(args.out)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"plan.lock written: {out}")
    print(f"interface_contract_hash: {payload['interface_contract_hash']}")
    print(f"plan_content_hash: {payload['plan_content_hash']}")
    deps = payload.get("dependency_hashes") or {}
    if deps:
        print(f"local imports pinned: {len(deps)}")
    else:
        print("local imports pinned: 0")
    dynamic = detect_dynamic_imports(script.implementation)
    if dynamic:
        print(
            "dynamic import: tool uses "
            + ", ".join(dynamic)
            + "; local deps cannot be fully pinned"
        )
    policy = script.specification.policy
    if getattr(policy, "pure", False):
        print(
            "declared_pure: Policy.pure is declared; "
            "runtime does not instrument I/O. File writes still PASS unless the body records effects."
        )


def _dummy_script(path: str | Path) -> ScriptModule:
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


def cmd_run(args: argparse.Namespace) -> None:
    """Walking skeleton or a user script via judge_script."""
    if args.script:
        input_val = parse_cli_input(args.input, default=3)
        from acid_engine.judge import SELF_LOCK_SKIP, judge_script
        from acid_engine.level3.pipeline import PipelineResult
        from acid_engine.level3.script.runner import load_script_lock

        if not args.plan:
            if not Path(args.script).exists():
                print(f"ERROR: Failed to load script: Script file not found: {args.script}")
                sys.exit(1)
            dummy = _dummy_script(args.script)
            skipped = ConformanceResult.skipped(SELF_LOCK_SKIP)
            result = PipelineResult(conformance=skipped)
            print(explain_result(result.conformance))
            _maybe_write_receipt(args, dummy, input_val, result, plan=None)
            sys.exit(1)
        try:
            raw = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            iface, plan = load_script_lock(raw)
        except Exception as e:
            print(f"ERROR: Failed to load plan: {e}")
            sys.exit(1)
        gate = source_hash_gate(args.script, raw)
        if gate is not None:
            dummy = _dummy_script(args.script)
            result = PipelineResult(conformance=gate)
            print(explain_block(result.conformance))
            _maybe_write_receipt(args, dummy, input_val, result, plan=plan, toolchain=raw)
            sys.exit(1)
        try:
            script = load_script_from_file(args.script)
        except Exception as e:
            print(f"ERROR: Failed to load script: {e}")
            sys.exit(1)
        from acid_engine.level2.implementation_canon import live_canon_kind
        from acid_engine.worker import verify_runtime_pin

        pin = verify_runtime_pin(
            raw, live_canon_kind=live_canon_kind(script.implementation)
        )
        if pin is not None:
            result = PipelineResult(conformance=pin)
            print(explain_block(result.conformance))
            _maybe_write_receipt(args, script, input_val, result, plan=plan, toolchain=raw)
            sys.exit(1)
        print("runtime: pinned")
        result = judge_script(
            script, input_val, plan=plan, iface=iface, toolchain=raw
        )
        print(explain_block(result.conformance))
        print(f"output: {result.data}")
        print(f"interface_contract_hash: {plan.interface_contract_hash}")
        print(f"plan_content_hash: {plan.content_hash}")
        _maybe_write_receipt(args, script, input_val, result, plan=plan, toolchain=raw)
        if not result.ok:
            sys.exit(1)
    else:
        from examples.walking_skeleton.run_x_plus_1 import main as ws_main
        ws_main()


def _maybe_write_receipt(
    args: argparse.Namespace,
    script: Any,
    input_val: Any,
    result: Any,
    plan: Any,
    toolchain: Any | None = None,
) -> None:
    path = getattr(args, "receipt", None)
    if not path:
        return
    from acid_engine.receipt import build_receipt, write_receipt

    payload = build_receipt(
        script,
        input_val,
        result,
        plan=plan,
        toolchain=toolchain,
        context=_receipt_context(args),
    )
    write_receipt(path, payload)
    print(f"receipt: {path}")


def _receipt_context(args: argparse.Namespace) -> dict[str, str]:
    out: dict[str, str] = {}
    agent = getattr(args, "agent", None)
    repo = getattr(args, "repository", None)
    if isinstance(agent, str) and agent.strip():
        out["agent"] = agent.strip()
    if isinstance(repo, str) and repo.strip():
        out["repository"] = repo.strip()
    return out


def cmd_judge(args: argparse.Namespace) -> None:
    """Public entry: bind before run + verdict. Same as run --script --plan."""
    if not args.script:
        print("ERROR: lock not passed — judge requires --script")
        sys.exit(1)
    cmd_run(args)


def cmd_locks(args: argparse.Namespace) -> None:
    """Check live bodies against plan.lock via an index. Does not execute, not hosted."""
    from acid_engine.level3.script.resolve import materialize_script
    from acid_engine.level3.script.runner import bind_script_to_plan, load_script_lock

    index_path = Path(args.index)
    if not index_path.is_file():
        print(f"ERROR: index not found: {index_path}")
        sys.exit(1)
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    from acid_engine.worker import RUNTIME_PIN_PATHS, runtime_hashes, source_hash

    pinned = raw.get("worker_hash")
    if not pinned:
        print("[FAIL] worker_hash missing")
        sys.exit(1)
    if str(pinned) != source_hash():
        print("[FAIL] worker_hash mismatch")
        sys.exit(1)
    pinned_rt = raw.get("runtime_hashes")
    if not isinstance(pinned_rt, dict) or not pinned_rt:
        print("[FAIL] runtime_hashes missing")
        sys.exit(1)
    live_rt = runtime_hashes()
    for rel in RUNTIME_PIN_PATHS:
        if pinned_rt.get(rel) != live_rt[rel]:
            print(f"[FAIL] runtime_hashes mismatch: {rel}")
            sys.exit(1)
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        print("ERROR: index has no entries")
        sys.exit(1)
    failed = 0
    for i, item in enumerate(entries):
        if not isinstance(item, dict):
            print(f"ERROR: entry {i} is not an object")
            sys.exit(1)
        ident = str(item.get("id") or i)
        script_rel = item.get("script")
        plan_rel = item.get("plan")
        if not plan_rel:
            print(f"[FAIL] {ident} lock not passed")
            failed += 1
            continue
        if not script_rel:
            print(f"[FAIL] {ident} script required")
            failed += 1
            continue
        script_path = Path(str(script_rel))
        plan_path = Path(str(plan_rel))
        if not script_path.is_file():
            print(f"[FAIL] {ident} script missing: {script_path}")
            failed += 1
            continue
        if not plan_path.is_file():
            print(f"[FAIL] {ident} plan missing: {plan_path}")
            failed += 1
            continue
        try:
            plan_raw = json.loads(plan_path.read_text(encoding="utf-8"))
            gate = source_hash_gate(script_path, plan_raw)
            if gate is not None:
                status = gate.status.value if hasattr(gate.status, "value") else str(gate.status)
                print(f"[{status}] {ident} {gate.message}")
                failed += 1
                continue
            script = materialize_script(load_script_from_file(script_path))
            _iface, plan = load_script_lock(plan_raw)
        except Exception as e:
            print(f"[FAIL] {ident} {e}")
            failed += 1
            continue
        bound = bind_script_to_plan(plan, script)
        if bound is not None:
            status = bound.status.value if hasattr(bound.status, "value") else str(bound.status)
            print(f"[{status}] {ident} {bound.message}")
            failed += 1
            continue
        print(f"[BOUND] {ident}")
        if not getattr(args, "judge", False):
            continue
        from acid_engine.judge import judge_script
        from acid_engine.receipt import build_receipt, write_receipt

        raw_plan = json.loads(plan_path.read_text(encoding="utf-8"))
        iface, plan = load_script_lock(raw_plan)
        result = judge_script(
            script, item.get("input"), plan=plan, iface=iface, toolchain=raw_plan
        )
        print(explain_block(result.conformance))
        dest = Path(getattr(args, "receipts", None) or "receipts")
        dest.mkdir(parents=True, exist_ok=True)
        rec_path = dest / f"{ident}.json"
        write_receipt(
            rec_path,
            build_receipt(
                script, item.get("input"), result, plan=plan, toolchain=raw_plan
            ),
        )
        print(f"receipt: {rec_path}")
        if not result.ok:
            failed += 1
    checked = len(entries)
    print("")
    print("Acid Judge")
    print(f"Tools checked: {checked}")
    print(f"Failed: {failed}")
    if getattr(args, "judge", False):
        print(f"Execution integrity: {'FAIL' if failed else 'PASS'}")
    else:
        print("Bind only. Bodies were not executed.")
    if failed:
        sys.exit(1)


def cmd_diff(args: argparse.Namespace) -> None:
    """Live vs plan.lock. Does not execute, not a verdict."""
    from acid_engine.level3.script.resolve import materialize_script
    from acid_engine.lock_diff import diff_lock, format_diff

    try:
        raw = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    if not isinstance(raw, dict):
        print("ERROR: plan must be a JSON object")
        sys.exit(1)
    gate = source_hash_gate(args.script, raw)
    if gate is not None:
        print(explain_block(gate))
        sys.exit(1)
    try:
        script = materialize_script(load_script_from_file(args.script))
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    rows = diff_lock(raw, script)
    print(format_diff(rows))
    if any(not row.ok for row in rows):
        sys.exit(1)


def cmd_receipt(args: argparse.Namespace) -> None:
    """Ed25519 on the receipt canon. Local key, not Sigstore."""
    from acid_engine.sign import keygen, sign_receipt, verify_receipt

    modes = [bool(args.keygen), bool(args.sign), bool(args.verify)]
    if sum(modes) != 1:
        print("ERROR: receipt needs exactly one of --keygen, --sign, --verify")
        sys.exit(1)
    try:
        if args.keygen:
            dest = args.out_dir or args.out
            if not dest:
                print("ERROR: --keygen needs --out-dir")
                sys.exit(1)
            secret, public = keygen(dest)
            print(f"secret: {secret}")
            print(f"public: {public}")
            return
        if args.sign:
            if not args.key:
                print("ERROR: --sign needs --key")
                sys.exit(1)
            receipt = json.loads(Path(args.sign).read_text(encoding="utf-8"))
            if not isinstance(receipt, dict):
                raise ValueError("receipt must be a JSON object")
            payload = sign_receipt(receipt, args.key)
            out = Path(args.out or (str(args.sign) + ".sig.json"))
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"signature: {out}")
            return
        if not args.sig or not args.pubkey:
            print("ERROR: --verify needs --sig and --pubkey")
            sys.exit(1)
        receipt = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        signature = json.loads(Path(args.sig).read_text(encoding="utf-8"))
        if not isinstance(receipt, dict) or not isinstance(signature, dict):
            raise ValueError("receipt and signature must be JSON objects")
        verify_receipt(receipt, signature, args.pubkey)
        print("[OK] signature verified")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def _add_script_plan_input(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--script", help="Path to a .py (`script` variable) or .json blank")
    parser.add_argument(
        "--plan",
        help="JSON plan.lock (acid_engine lock --script). Without it SKIPPED",
    )
    parser.add_argument(
        "--input",
        help="Input: int, JSON (e.g. '[1,2,3]'), or a string. Default 3",
    )
    parser.add_argument(
        "--receipt",
        help="Where to write receipt.json (fact + verdict, no proven_pure)",
    )
    parser.add_argument(
        "--agent",
        help="Optional receipt context: who invoked. Not identity.",
    )
    parser.add_argument(
        "--repository",
        help="Optional receipt context: repo id. Not identity.",
    )


def _hidden_cli(argv: list[str]) -> None:
    """init/validate still run, but they are not on the public --help."""
    parser = argparse.ArgumentParser(prog="acid-engine")
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--path", default="script.py", help="Path to the script .py file")
    p_init.add_argument("--script", help="Alternate path for the script template")
    p_init.set_defaults(func=cmd_init)
    p_val = sub.add_parser("validate")
    p_val.add_argument("spec", help="Path to a .py file that defines contract")
    p_val.add_argument("command", nargs="*", help="Command to check")
    p_val.set_defaults(func=cmd_validate)
    p_run = sub.add_parser("run")
    _add_script_plan_input(p_run)
    p_run.set_defaults(func=cmd_run)
    args = parser.parse_args(argv)
    args.func(args)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"init", "validate", "run"}:
        _hidden_cli(sys.argv[1:])
        return
    parser = argparse.ArgumentParser(
        prog="acid-judge",
        description="Acid Judge: lock, judge, receipt.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_judge = subparsers.add_parser(
        "judge",
        help="Bind plan.lock before execution + verdict",
    )
    _add_script_plan_input(p_judge)
    p_judge.set_defaults(func=cmd_judge)

    p_lock = subparsers.add_parser("lock", help="Lock the body (JSON plan.lock)")
    p_lock.add_argument("--script", required=True, help="Path to a .py or .json blank")
    p_lock.add_argument("--out", required=True, help="Where to write lock JSON")
    p_lock.set_defaults(func=cmd_lock)

    p_locks = subparsers.add_parser(
        "locks",
        help="Check live bodies against plan.lock via an index. Without --judge does not execute.",
    )
    p_locks.add_argument("--index", required=True, help="locks/index.json")
    p_locks.add_argument(
        "--judge",
        action="store_true",
        help="After bind, execute the body and write a receipt. Default is bind only.",
    )
    p_locks.add_argument("--receipts", default="receipts", help="Receipt directory when --judge")
    p_locks.set_defaults(func=cmd_locks)

    p_diff = subparsers.add_parser(
        "diff",
        help="Live vs plan.lock (does not execute, not a verdict)",
    )
    p_diff.add_argument("--script", required=True, help="Path to a .py or .json blank")
    p_diff.add_argument("--plan", required=True, help="JSON plan.lock")
    p_diff.set_defaults(func=cmd_diff)

    p_receipt = subparsers.add_parser(
        "receipt",
        help="Ed25519 sign/verify canonical receipt (local openssl, not Sigstore)",
    )
    p_receipt.add_argument("--keygen", action="store_true", help="Create an Ed25519 key pair")
    p_receipt.add_argument("--sign", help="Path to receipt.json")
    p_receipt.add_argument("--verify", help="Path to receipt.json")
    p_receipt.add_argument("--key", help="Secret PEM")
    p_receipt.add_argument("--pubkey", help="Public PEM")
    p_receipt.add_argument("--sig", help="Signature JSON")
    p_receipt.add_argument("--out", help="Where to write the signature or keys")
    p_receipt.add_argument("--out-dir", help="Directory for --keygen")
    p_receipt.set_defaults(func=cmd_receipt)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
