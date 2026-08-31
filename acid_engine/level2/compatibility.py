"""Minimal contract compatibility analysis."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CompatibilityKind(str, Enum):
    IDENTICAL = "IDENTICAL"
    BACKWARD_COMPATIBLE = "BACKWARD_COMPATIBLE"
    FORWARD_COMPATIBLE = "FORWARD_COMPATIBLE"
    BREAKING = "BREAKING"


@dataclass(frozen=True, slots=True)
class CompatibilityResult:
    kind: CompatibilityKind
    message: str = ""


def compare_types(old: str, new: str) -> CompatibilityResult:
    """Very simple structural type comparison for MVP."""
    if old == new:
        return CompatibilityResult(CompatibilityKind.IDENTICAL)
    if old == "int" and new == "float":
        return CompatibilityResult(
            CompatibilityKind.BACKWARD_COMPATIBLE,
            "int can be widened to float",
        )
    if old == "float" and new == "int":
        return CompatibilityResult(
            CompatibilityKind.BREAKING,
            "float cannot be narrowed to int",
        )
    if old in new:
        return CompatibilityResult(
            CompatibilityKind.BACKWARD_COMPATIBLE,
            f"{old!r} appears to be a subset of {new!r}",
        )
    return CompatibilityResult(
        CompatibilityKind.BREAKING,
        f"Type change {old!r} → {new!r} is breaking",
    )


def compare_contracts(old_hash: str, new_hash: str) -> CompatibilityResult:
    """Сравнение контрактов по хешам (минимально)."""
    if old_hash == new_hash:
        return CompatibilityResult(CompatibilityKind.IDENTICAL)
    return CompatibilityResult(
        CompatibilityKind.BREAKING,
        "Contracts differ; manual review required",
    )