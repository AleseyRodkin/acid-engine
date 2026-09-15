"""Async runner for AsyncScriptModule."""
from __future__ import annotations

import time
from typing import Any

from acid_engine.level1.effects import EffectCollector
from acid_engine.level3.container.delta import ContainerDelta
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.state import ExecutionState
from acid_engine.level3.script.async_module import AsyncScriptModule
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level3.script.resolve import resolve_script


async def run_async_script(
    script: AsyncScriptModule,
    input_snapshot: ContainerSnapshot,
    mode: ExecutionMode = ExecutionMode.NORMAL,
    logger: Any = None,
) -> tuple[ContainerSnapshot, ExecutionObservation, ContainerDelta, ExecutionState]:
    """
    Run an async ScriptModule.
    Returns output snapshot, observation, delta, state.
    """
    state = ExecutionState()
    state.mark_running()
    start = time.perf_counter()
    trace: list[str] = []
    collector = EffectCollector()

    if mode == ExecutionMode.NORMAL:
        trace.append(f"start:{script.name or script.contract_id.name}")
    else:
        trace.append("start:light")

    try:
        fn, unresolved = resolve_script(script)
        if unresolved is not None:
            end = time.perf_counter()
            if unresolved == "missing_implementation":
                state.mark_skipped()
                status = "skipped"
            else:
                state.mark_failed(unresolved)
                status = "failed"
            obs = ExecutionObservation.create(
                start=start,
                end=end,
                status=status,
                effects=(),
                trace=tuple(trace) + (f"{status}:{unresolved}",),
                input_hash=input_snapshot.content_hash if mode == ExecutionMode.NORMAL else "",
                logger=logger,
            )
            delta = ContainerDelta(
                input_cardinality=input_snapshot.cardinality,
                output_cardinality=0,
                input_hash=input_snapshot.content_hash if mode == ExecutionMode.NORMAL else "",
                output_hash="",
                status=status,
                latency_ms=obs.latency_ms,
            )
            out_port = PortRef(
                module=script.contract_id.name,
                direction="output",
                name="result",
            )
            empty = ContainerSnapshot.create(
                port_ref=out_port,
                contract_id=script.contract_id,
                contract_hash=script.content_hash,
                data=None,
                cardinality=0,
            )
            return empty, obs, delta, state
        assert fn is not None
        with collector:
            result = await fn(input_snapshot.data)
        end = time.perf_counter()
        state.mark_completed()
        trace.append("completed")
        effects = tuple(collector.effects) if mode == ExecutionMode.NORMAL else ()

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
            provenance=f"async_run:{script.contract_id}",
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
        effects = tuple(collector.effects) if mode == ExecutionMode.NORMAL else ()
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