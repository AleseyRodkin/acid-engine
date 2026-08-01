"""ExecutionObservation — facts of a concrete run."""
from __future__ import annotations

from dataclasses import dataclass
import time
import uuid
import json


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
        # Structured log (можно перенаправить в файл)
        log_entry = {
            "run_id": obs.run_id,
            "status": obs.status,
            "latency_ms": round(obs.latency_ms, 3),
            "input_hash": obs.input_hash,
            "output_hash": obs.output_hash,
            "trace": list(obs.trace),
        }
        print(f"[ACID_EXEC] {json.dumps(log_entry, ensure_ascii=False)}")
        return obs