"""ExecutionObservation — facts of a concrete run."""
from __future__ import annotations

from dataclasses import dataclass
import time
import uuid
from typing import Optional


@dataclass(frozen=True, slots=True)
class ExecutionObservation:
    run_id: str
    start_time: float
    end_time: float
    latency_ms: float
    status: str
    effects_observed: tuple[str, ...] = ()
    trace: tuple[str, ...] = ()
    input_hash: str = ""
    output_hash: str = ""

    @staticmethod
    def create(
        start: float,
        end: float,
        status: str,
        effects: tuple[str, ...] = (),
        trace: tuple[str, ...] = (),
        input_hash: str = "",
        output_hash: str = "",
        logger=None,  # ExecutionLogger или None
    ) -> ExecutionObservation:
        obs = ExecutionObservation(
            run_id=str(uuid.uuid4()),
            start_time=start,
            end_time=end,
            latency_ms=(end - start) * 1000.0,
            status=status,
            effects_observed=effects,
            trace=trace,
            input_hash=input_hash,
            output_hash=output_hash,
        )
        # Лог только opt-in: через переданный logger. Ядро не печатает в stdout.
        if logger is not None:
            logger.log(obs)
        return obs