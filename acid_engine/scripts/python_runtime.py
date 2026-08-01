"""Minimal Python implementation runner."""
from __future__ import annotations

import time
from typing import Any
from acid_engine.scripts.module import ScriptModule
from acid_engine.containers.snapshot import ContainerSnapshot
from acid_engine.containers.observation import ExecutionObservation
from acid_engine.containers.delta import ContainerDelta
from acid_engine.containers.state import ExecutionState, ExecutionStatus
from acid_engine.containers.port import PortRef
from acid_engine.execution.modes import ExecutionMode


def run_script(
    script: ScriptModule,
    input_snapshot: ContainerSnapshot,
    mode: ExecutionMode = ExecutionMode.NORMAL,
    logger=None,
) -> tuple[ContainerSnapshot, ExecutionObservation, ContainerDelta, ExecutionState]:
    state = ExecutionState()
    state.mark_running()
    start = time.perf_counter()
    effects: list[str] = []
    trace: list[str] = []

    if mode == ExecutionMode.NORMAL:
        trace.append(f"start:{script.name or script.contract_id.name}")
    else:
        trace.append("start:light")

    try:
        result = script.implementation(input_snapshot.data)
        end = time.perf_counter()
        state.mark_completed()
        trace.append("completed")

        out_port = PortRef(
            module=script.contract_id.name,
            direction="output",
            name="result",
        )
        output_snapshot = ContainerSnapshot.create(
            port_ref=out_port,
            contract_id=script.contract_id,
            contract_hash=script.content_hash,
            data=result,
            cardinality=1,
            provenance=f"run:{script.contract_id}",
        )

        obs = ExecutionObservation.create(
            start=start,
            end=end,
            status="completed",
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
            status="completed",
            latency_ms=obs.latency_ms,
        )
        return output_snapshot, obs, delta, state

    except Exception as e:
        end = time.perf_counter()
        state.mark_failed(str(e))
        trace.append(f"failed:{e}")
        obs = ExecutionObservation.create(
            start=start,
            end=end,
            status="failed",
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
        out_port = PortRef(
            module=script.contract_id.name,
            direction="output",
            name="result",
        )
        failed_snap = ContainerSnapshot.create(
            port_ref=out_port,
            contract_id=script.contract_id,
            contract_hash=script.content_hash,
            data=None,
            cardinality=0,
        )
        return failed_snap, obs, delta, state