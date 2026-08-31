"""External runner: исполнение произвольной команды с расширенными возможностями."""
from __future__ import annotations

import subprocess
import time
from typing import Any

from acid_engine.level2.identity import ContractId
from acid_engine.level3.container.delta import ContainerDelta
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.state import ExecutionState
from acid_engine.level3.script.modes import ExecutionMode


def run_external(
    command: list[str],
    contract_id: ContractId,
    contract_hash: str,
    input_data: Any = None,
    mode: ExecutionMode = ExecutionMode.NORMAL,
    logger: Any = None,
    timeout: float | None = None,
    stdin_data: str | None = None,       # данные для stdin процесса
    text_mode: bool = True,                 # text mode (str) или bytes
) -> tuple[ContainerSnapshot, ExecutionObservation, ContainerDelta, ExecutionState]:
    """
    Запускает внешнюю команду, собирает stdout/stderr, exit code и latency.
    Возвращает output snapshot, observation, delta, state.
    """
    state = ExecutionState()
    state.mark_running()
    start = time.perf_counter()

    # Формируем input snapshot
    in_port = PortRef(module=contract_id.name, direction="input", name="stdin")
    input_snapshot = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=contract_id,
        contract_hash=contract_hash,
        data=input_data if input_data is not None else (stdin_data or ""),
    )

    effects: list[str] = []
    trace: list[str] = [f"start_external:{command[0]}"]

    try:
        proc = subprocess.run(
            command,
            timeout=timeout,
            capture_output=True,
            text=text_mode,
            input=stdin_data,
        )
        end = time.perf_counter()

        stdout = (proc.stdout.strip() if isinstance(proc.stdout, str) else proc.stdout)
        stderr = (proc.stderr.strip() if isinstance(proc.stderr, str) else proc.stderr)
        exit_code = proc.returncode

        output_data = {
            "stdout": stdout or "",
            "stderr": stderr or "",
            "exit_code": exit_code,
        }
        status_str = "completed" if exit_code == 0 else "failed"
        state.mark_completed() if exit_code == 0 else state.mark_failed(str(stderr))
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

    except subprocess.TimeoutExpired:
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