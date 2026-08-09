"""Исполнение по замороженному плану с возможностью replay."""
from __future__ import annotations

from typing import Any, Dict, Optional
import time
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.container.delta import ContainerDelta
from acid_engine.level3.container.state import ExecutionState
from acid_engine.level3.container.port import PortRef
from acid_engine.level2.conformance import (
    ConformanceResult, check_conformance, explain_result,
)
from acid_engine.level3.script.module import ScriptModule


def execute_plan(
    iface: InterfaceContract,
    plan: PlanLock,
    script: ScriptModule,
    input_data: Any,
) -> ConformanceResult:
    """
    Исполняет скрипт в соответствии с планом и возвращает результат конформности.
    Использует режим из плана.
    """
    from acid_engine.level3.script.python_runtime import run_script

    in_port = PortRef(module=script.contract_id.name, direction="input", name="value")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=input_data,
    )
    output_snap, obs, delta, state = run_script(
        script, input_snap, mode=plan.execution_mode,
    )
    result = check_conformance(
        required_output_type=script.output_type,
        provided_data=output_snap.data,
        obs=obs,
        policy=script.specification.policy,
        node_id=script.name,
        contract_id=str(script.contract_id),
    )
    return result


def replay_run(
    plan: PlanLock,
    script: ScriptModule,
    input_data: Any,
    expected_output: Optional[Any] = None,
) -> bool:
    """
    Переигрывает выполнение по plan.lock и проверяет воспроизводимость.
    Возвращает True, если результат совпадает с ожидаемым.
    """
    from acid_engine.level3.script.python_runtime import run_script

    in_port = PortRef(module=script.contract_id.name, direction="input", name="value")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=input_data,
    )
    output_snap, obs, delta, state = run_script(
        script, input_snap, mode=plan.execution_mode,
    )
    if expected_output is not None:
        return output_snap.data == expected_output
    # без ожидаемого результата — считаем, что выполнение без ошибок = воспроизводимость
    return state.status == "completed"