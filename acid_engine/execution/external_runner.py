"""External runner: исполнение произвольной команды (подпроцесс) с захватом фактов."""
from __future__ import annotations

import subprocess
import time
from typing import Any, Optional
from acid_engine.containers.snapshot import ContainerSnapshot
from acid_engine.containers.observation import ExecutionObservation
from acid_engine.containers.delta import ContainerDelta
from acid_engine.containers.state import ExecutionState, ExecutionStatus
from acid_engine.containers.port import PortRef
from acid_engine.contracts.identity import ContractId
from acid_engine.execution.modes import ExecutionMode


def run_external(
    command: list[str],
    contract_id: ContractId,
    contract_hash: str,
    input_data: Any = None,
    mode: ExecutionMode = ExecutionMode.NORMAL,
    logger=None,
    timeout: Optional[float] = None,
) -> tuple[ContainerSnapshot, ExecutionObservation, ContainerDelta, ExecutionState]:
    """
    Запускает внешнюю команду, собирает stdout/stderr, exit code и latency.
    Возвращает output snapshot, observation, delta, state.
    """
    state = ExecutionState()
    state.mark_running()
    start = time.perf_counter()

    # Формируем input snapshot (может быть пустым)
    in_port = PortRef(module=contract_id.name, direction="input", name="stdin")
    input_snapshot = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=contract_id,
        contract_hash=contract_hash,
        data=input_data if input_data is not None else "",
    )

    effects: list[str] = []
    trace: list[str] = [f"start_external:{command[0]}"]

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        end = time.perf_counter()

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        exit_code = proc.returncode

        # Собираем результат как словарь (можно интерпретировать как JSON)
        output_data = {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
        }
        status_str = "completed" if exit_code == 0 else "failed"

        state.mark_completed() if exit_code == 0 else state.mark_failed(stderr)
        trace.append(f"exit_code:{exit_code}")

        out_port = PortRef(module=contract_id.name, direction="output", name="result")
        output_snapshot = ContainerSnapshot.create(
            port_ref=out_port,
            contract_id=contract_id,
            contract_hash=contract_hash,
            data=output_data,
            provenance=f"external_run:{contract_id}",
        )

        obs = ExecutionObservation.create(
            start=start,
            end=end,
            status=status_str,
            effects=tuple(effects) if mode == ExecutionMode.NORMAL else (),
            trace=tuple(trace),
            input_hash=input_snapshot.content_hash if mode == ExecutionMode.NORMAL else "",
            output_hash=output_snapshot.content_hash if mode == ExecutionMode.NORMAL else "",
            logger=logger,
        )

        delta = ContainerDelta(
            input_cardinality=input_snapshot.cardinality,
            output_cardinality=output_snapshot.cardinality,
            input_hash=input_snapshot.content_hash if mode == ExecutionMode.NORMAL else "",
            output_hash=output_snapshot.content_hash if mode == ExecutionMode.NORMAL else "",
            status=status_str,
            latency_ms=obs.latency_ms,
        )
        return output_snapshot, obs, delta, state

    except subprocess.TimeoutExpired as e:
        end = time.perf_counter()
        state.mark_failed(f"timeout after {timeout}s")
        trace.append("timeout")
        obs = ExecutionObservation.create(
            start=start, end=end, status="failed",
            effects=tuple(effects) if mode == ExecutionMode.NORMAL else (),
            trace=tuple(trace),
            input_hash=input_snapshot.content_hash if mode == ExecutionMode.NORMAL else "",
            logger=logger,
        )
        delta = ContainerDelta(
            input_cardinality=input_snapshot.cardinality,
            output_cardinality=0,
            input_hash=input_snapshot.content_hash if mode == ExecutionMode.NORMAL else "",
            output_hash="",
            status="failed",
            latency_ms=obs.latency_ms,
        )
        out_port = PortRef(module=contract_id.name, direction="output", name="result")
        failed_snap = ContainerSnapshot.create(
            port_ref=out_port,
            contract_id=contract_id,
            contract_hash=contract_hash,
            data=None,
            cardinality=0,
        )
        return failed_snap, obs, delta, state