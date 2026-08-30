"""Исполнение по замороженному плану. plan.lock связывает тело реализации."""
from __future__ import annotations

from typing import Any, Optional

from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.port import PortRef
from acid_engine.level2.conformance import (
    ConformanceResult,
    ConformanceStatus,
    ConformanceLevel,
    check_conformance,
)
from acid_engine.level2.failure import FailureReason
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.pipeline import PipelineResult


def _locked_hash_for(plan: PlanLock, script: ScriptModule) -> tuple[Optional[str], str]:
    hashes = plan.module_hashes
    for key in (script.name, script.contract_id.name, str(script.contract_id)):
        if key and key in hashes:
            return hashes[key], key
    if len(hashes) == 1:
        key, value = next(iter(hashes.items()))
        return value, key
    return None, ""


def bind_script_to_plan(plan: PlanLock, script: ScriptModule) -> Optional[ConformanceResult]:
    """
    None = bound, можно исполнять.
    SKIPPED = в lock нет факта, чем сверять.
    FAIL = тело не то, что заморожено. Реализацию не запускать.
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
    return None


def lock_for_script(script: ScriptModule):
    """Заморозить plan.lock на текущее тело скрипта. Публичный PASS только после bind."""
    from acid_engine.level3.script.modes import ExecutionMode

    iface = InterfaceContract(
        contract_id=script.contract_id,
        version=script.version,
        inputs={"value": script.input_type},
        outputs={"result": script.output_type},
        constraints=script.specification.policy.to_canonical_dict()
        if hasattr(script.specification, "policy")
        else {},
        module_hashes={script.name or script.contract_id.name: script.content_hash},
    )
    plan = PlanLock.create(
        plan_id=f"lock-{script.name or script.contract_id.name}",
        interface_contract_hash=iface.content_hash,
        resolved_policies=iface.constraints,
        module_hashes=iface.module_hashes,
        execution_mode=ExecutionMode.NORMAL,
    )
    return iface, plan


def execute_plan(
    iface: InterfaceContract,
    plan: PlanLock,
    script: ScriptModule,
    input_data: Any,
) -> PipelineResult:
    """Исполняет скрипт только если он совпадает с plan.lock."""
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

    from acid_engine.level3.script.python_runtime import run_script
    from acid_engine.level3.script.resolve import resolve_script, unresolved_conformance

    _fn, unresolved = resolve_script(script)
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
        script, input_snap, mode=plan.execution_mode,
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
    expected_output: Optional[Any] = None,
) -> ConformanceResult:
    """
    Replay по plan.lock.
    Без expected_output — SKIPPED («не упало» ≠ replay).
    Хеш не совпал — FAIL, тело не запускается.
    Выход ≠ expected — FAIL.
    """
    bound = bind_script_to_plan(plan, script)
    if bound is not None:
        return bound

    if expected_output is None:
        return ConformanceResult.skipped(
            "replay without expected_output is not a fact"
        )

    from acid_engine.level3.script.python_runtime import run_script
    from acid_engine.level3.script.resolve import resolve_script, unresolved_conformance

    _fn, unresolved = resolve_script(script)
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
        script, input_snap, mode=plan.execution_mode,
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
