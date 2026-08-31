"""Человекочитаемые объяснения конформности и решений резолвера."""
from __future__ import annotations

from acid_engine.level2.conformance import ConformanceResult
from acid_engine.level2.resolver import ResolveConflict


def explain_conformance(result: ConformanceResult) -> str:
    """Подробное объяснение результата сравнения Provided vs Required."""
    if result.ok:
        return f"[PASS] {result.message}"
    if result.failure:
        return result.failure.human()
    return f"[{result.status.value}] {result.message}"


def explain_conflict(conflict: ResolveConflict) -> str:
    """Объяснение конфликта при разрешении политик."""
    return (
        f"Policy conflict on '{conflict.field_name}': "
        f"parent requires {conflict.parent_value}, child declares {conflict.child_value}. "
        f"{conflict.message}"
    )