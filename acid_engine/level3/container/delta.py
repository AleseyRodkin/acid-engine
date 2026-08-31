"""ContainerDelta — minimal change summary between input and output."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContainerDelta:
    input_cardinality: int
    output_cardinality: int
    input_hash: str
    output_hash: str
    status: str
    latency_ms: float

    @property
    def cardinality_delta(self) -> int:
        return self.output_cardinality - self.input_cardinality