"""Port identity."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PortRef:
    """Stable reference to a data port, e.g. normalize_news.input.articles"""
    module: str
    direction: str  # "input" | "output"
    name: str

    def __str__(self) -> str:
        return f"{self.module}.{self.direction}.{self.name}"

    @staticmethod
    def parse(s: str) -> PortRef:
        parts = s.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid PortRef: {s!r}")
        return PortRef(module=parts[0], direction=parts[1], name=parts[2])