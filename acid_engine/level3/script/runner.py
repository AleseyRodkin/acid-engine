"""Execute against a frozen plan. plan.lock binds the implementation body."""
from __future__ import annotations

import sys
from collections.abc import Mapping
from typing import Any

from acid_engine.level2.conformance import (
    ConformanceLevel,
    ConformanceResult,
    ConformanceStatus,
    check_conformance,
)
from acid_engine.level2.failure import FailureReason
from acid_engine.level2.implementation_canon import canon_id_for, live_canon_kind
from acid_engine.level2.local_deps import collect_local_dep_hashes, seal_local_deps
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.pipeline import PipelineResult
from acid_engine.level3.script.module import ScriptModule


def _locked_hash_for(plan: PlanLock, script: ScriptModule) -> tuple[str | None, str]:
    hashes = plan.module_hashes
    for key in (script.name, script.contract_id.name, str(script.contract_id)):
        if key and key in hashes:
            return hashes[key], key
    return None, ""


def bind_script_to_plan(plan: PlanLock, script: ScriptModule) -> ConformanceResult | None:
    """
    None = bound, may execute.
    SKIPPED = the lock has no fact to check against.
    FAIL = the body is not what was frozen. Do not run the implementation.
    """
    if not plan.module_hashes:
        return ConformanceResult.skipped(
            "plan.lock has no module_hashes; cannot bind implementation"
        )
    expected, key = _locked_hash_for(plan, script)
    if expected is None:
        return ConformanceResult.skipped(
            f"plan.lock has no module hash for {script.name!r}"
        )
    actual = script.content_hash
    if actual != expected:
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message="plan.lock module hash mismatch",
            failure=FailureReason(
                node_id=script.name,
                contract_id=str(script.contract_id),
                property_name="module_hash",
                expected=expected,
                actual=actual,
                detail=f"lock_key={key}",
            ),
        )
    live_deps = collect_local_dep_hashes(script.implementation)
    locked_deps = {
        name[4:]: digest
        for name, digest in plan.module_hashes.items()
        if name.startswith("dep:")
    }
    if locked_deps != live_deps:
        changed = sorted(
            set(locked_deps) ^ set(live_deps)
            | {
                name
                for name in locked_deps
                if name in live_deps and locked_deps[name] != live_deps[name]
            }
        )
        detail = ",".join(changed[:8]) or "dependency_hash"
        focus = changed[0] if changed else ""
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message="plan.lock dependency hash mismatch",
            failure=FailureReason(
                node_id=script.name,
                contract_id=str(script.contract_id),
                property_name="dependency_hash",
                expected=str(locked_deps.get(focus, "missing")),
                actual=str(live_deps.get(focus, "missing")),
                detail=detail,
            ),
        )
    return None


def lock_for_script(script: ScriptModule) -> tuple[InterfaceContract, PlanLock]:
    """Freeze plan.lock on the current script body. Public PASS only after bind."""
    from acid_engine.level3.script.modes import ExecutionMode
    from acid_engine.level3.script.resolve import materialize_script

    script = materialize_script(script)
    deps = collect_local_dep_hashes(script.implementation)
    hashes = {script.name or script.contract_id.name: script.content_hash}
    for rel, digest in deps.items():
        hashes[f"dep:{rel}"] = digest
    iface = InterfaceContract(
        contract_id=script.contract_id,
        version=script.version,
        inputs={"value": script.input_type},
        outputs={"result": script.output_type},
        constraints=script.specification.policy.to_canonical_dict()
        if hasattr(script.specification, "policy")
        else {},
        module_hashes=hashes,
    )
    plan = PlanLock.create(
        plan_id=f"lock-{script.name or script.contract_id.name}",
        interface_contract_hash=iface.content_hash,
        resolved_policies=iface.constraints,
        module_hashes=iface.module_hashes,
        execution_mode=ExecutionMode.NORMAL,
    )
    return iface, plan


def lock_toolchain(script: ScriptModule) -> dict[str, Any]:
    """python_version + canon_kind + runtime pins next to the lock. Not in identity."""
    kind = live_canon_kind(script.implementation)
    from acid_engine.worker import runtime_hashes, source_hash

    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "canon_kind": kind,
        "canon": canon_id_for(kind),
        "worker_hash": source_hash(),
        "runtime_hashes": runtime_hashes(),
    }


def dump_script_lock(script: ScriptModule) -> dict[str, Any]:
    """JSON-safe lock after materialize. Not a CLI tautology: the file is stored separately."""
    from acid_engine.level3.script.resolve import materialize_script

    script = materialize_script(script)
    iface, plan = lock_for_script(script)
    deps = collect_local_dep_hashes(script.implementation)
    return {
        "plan_id": plan.plan_id,
        "interface_contract_hash": plan.interface_contract_hash,
        "resolved_policies": plan.resolved_policies,
        "module_hashes": dict(plan.module_hashes),
        "dependency_hashes": dict(deps),
        "execution_mode": plan.execution_mode.value,
        "toolchain": lock_toolchain(script),
        "plan_content_hash": plan.content_hash,
        "iface": {
            "contract_id": str(iface.contract_id),
            "version": str(iface.version),
            "inputs": dict(iface.inputs),
            "outputs": dict(iface.outputs),
            "constraints": dict(iface.constraints),
            "module_hashes": dict(iface.module_hashes),
        },
    }


def load_script_lock(data: Mapping[str, Any]) -> tuple[InterfaceContract, PlanLock]:
    """Restore iface+plan from lock JSON. Without materializing the current body."""
    from acid_engine.level2.identity import ContractId, Version
    from acid_engine.level3.script.modes import ExecutionMode

    raw = data.get("iface")
    if not isinstance(raw, Mapping):
        raise ValueError("lock JSON must contain iface object")
    ver_s = str(raw.get("version") or "0.0.0")
    label = ""
    if "-" in ver_s:
        ver_s, label = ver_s.split("-", 1)
    nums = ver_s.split(".")
    version = Version(
        int(nums[0]) if nums else 0,
        int(nums[1]) if len(nums) > 1 else 0,
        int(nums[2]) if len(nums) > 2 else 0,
        label,
    )
    iface = InterfaceContract(
        contract_id=ContractId.parse(str(raw["contract_id"])),
        version=version,
        inputs=dict(raw.get("inputs") or {}),
        outputs=dict(raw.get("outputs") or {}),
        constraints=dict(raw.get("constraints") or {}),
        module_hashes=dict(raw.get("module_hashes") or {}),
    )
    mode_raw = str(data.get("execution_mode") or "normal")
    plan = PlanLock.create(
        plan_id=str(data.get("plan_id") or "lock"),
        interface_contract_hash=str(data["interface_contract_hash"]),
        resolved_policies=dict(data.get("resolved_policies") or {}),
        module_hashes=dict(data.get("module_hashes") or {}),
        execution_mode=ExecutionMode(mode_raw),
    )
    return iface, plan


def execute_plan(
    iface: InterfaceContract,
    plan: PlanLock,
    script: ScriptModule,
    input_data: Any,
    *,
    toolchain: Mapping[str, Any] | None = None,
) -> PipelineResult:
    """Run the script only if it matches plan.lock and the contour is pinned."""
    from acid_engine.level3.script.resolve import materialize_script
    from acid_engine.worker import verify_runtime_pin

    if toolchain is None:
        return PipelineResult(
            conformance=ConformanceResult.skipped("runtime not pinned")
        )
    pin = verify_runtime_pin(
        toolchain, live_canon_kind=live_canon_kind(script.implementation)
    )
    if pin is not None:
        return PipelineResult(conformance=pin)

    script = materialize_script(script)
    if plan.interface_contract_hash != iface.content_hash:
        return PipelineResult(
            conformance=ConformanceResult(
                status=ConformanceStatus.FAIL,
                level=ConformanceLevel.STRUCTURAL,
                message="plan.lock interface hash mismatch",
                failure=FailureReason(
                    node_id=script.name,
                    contract_id=str(iface.contract_id),
                    property_name="interface_contract_hash",
                    expected=plan.interface_contract_hash,
                    actual=iface.content_hash,
                ),
            )
        )

    bound = bind_script_to_plan(plan, script)
    if bound is not None:
        return PipelineResult(conformance=bound)

    leaked = seal_local_deps(script.implementation)
    if leaked is not None:
        return PipelineResult(
            conformance=ConformanceResult(
                status=ConformanceStatus.FAIL,
                level=ConformanceLevel.STRUCTURAL,
                message="plan.lock dependency hash mismatch",
                failure=FailureReason(
                    node_id=script.name,
                    contract_id=str(iface.contract_id),
                    property_name="dependency_hash",
                    expected="sealed",
                    actual="drift",
                    detail=leaked,
                ),
            )
        )

    from acid_engine.level3.script.python_runtime import run_script
    from acid_engine.level3.script.resolve import resolve_script, unresolved_conformance

    fn, unresolved = resolve_script(script)
    if unresolved is not None:
        return PipelineResult(conformance=unresolved_conformance(script, unresolved))

    in_port = PortRef(module=script.contract_id.name, direction="input", name="value")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=input_data,
    )
    output_snap, obs, _delta, _state = run_script(
        script, input_snap, mode=plan.execution_mode, fn=fn,
    )
    conf = check_conformance(
        required_output_type=script.output_type,
        provided_data=output_snap.data,
        obs=obs,
        policy=script.specification.policy,
        node_id=script.name,
        contract_id=str(script.contract_id),
    )
    return PipelineResult(
        conformance=conf,
        data=output_snap.data,
        observation=obs,
    )


def replay_run(
    plan: PlanLock,
    script: ScriptModule,
    input_data: Any,
    expected_output: Any | None = None,
) -> ConformanceResult:
    """
    Replay against plan.lock.
    Without expected_output — SKIPPED ("did not crash" ≠ replay).
    Hash mismatch — FAIL, the body is not run.
    Output ≠ expected — FAIL.
    """
    from acid_engine.level3.script.resolve import materialize_script

    script = materialize_script(script)
    bound = bind_script_to_plan(plan, script)
    if bound is not None:
        return bound

    if expected_output is None:
        return ConformanceResult.skipped(
            "replay without expected_output is not a fact"
        )

    from acid_engine.level3.script.python_runtime import run_script
    from acid_engine.level3.script.resolve import resolve_script, unresolved_conformance

    fn, unresolved = resolve_script(script)
    if unresolved is not None:
        return unresolved_conformance(script, unresolved)

    in_port = PortRef(module=script.contract_id.name, direction="input", name="value")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=input_data,
    )
    output_snap, obs, _delta, _state = run_script(
        script, input_snap, mode=plan.execution_mode, fn=fn,
    )
    if output_snap.data != expected_output:
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.OPERATIONAL,
            message="replay output mismatch",
            failure=FailureReason(
                node_id=script.name,
                contract_id=str(script.contract_id),
                property_name="output",
                expected=expected_output,
                actual=output_snap.data,
            ),
        )
    return check_conformance(
        required_output_type=script.output_type,
        provided_data=output_snap.data,
        obs=obs,
        policy=script.specification.policy,
        node_id=script.name,
        contract_id=str(script.contract_id),
    )
