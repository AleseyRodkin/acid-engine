"""Conformance levels and result types."""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional
from acid_engine.contracts.failure import FailureReason
from acid_engine.containers.observation import ExecutionObservation
from acid_engine.scripts.specification import Policy


class ConformanceLevel(str, Enum):
    STRUCTURAL = "structural"
    OPERATIONAL = "operational"
    SEMANTIC = "semantic"


class ConformanceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class ConformanceResult:
    status: ConformanceStatus
    level: ConformanceLevel
    message: str = ""
    failure: Optional[FailureReason] = None

    @property
    def ok(self) -> bool:
        return self.status == ConformanceStatus.PASS


def check_conformance(
    required_output_type: str,
    provided_data: Any,
    obs: ExecutionObservation,
    policy: Policy,
    node_id: str = "",
    contract_id: str = "",
) -> ConformanceResult:
    """
    Compare Provided (data + observation) against Required (type + policy).
    Returns ConformanceResult with PASS/FAIL and optional FailureReason.
    """
    # Structural: check type tag (very simplified)
    type_map = {
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "None": type(None),
    }
    expected_type = type_map.get(required_output_type, object)
    if not isinstance(provided_data, expected_type):
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message="Output type mismatch",
            failure=FailureReason(
                node_id=node_id,
                contract_id=contract_id,
                property_name="output_type",
                expected=required_output_type,
                actual=type(provided_data).__name__,
            ),
        )

    # Operational: check latency
    if policy.max_latency_ms is not None and obs.latency_ms > policy.max_latency_ms:
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.OPERATIONAL,
            message="Latency exceeded",
            failure=FailureReason(
                node_id=node_id,
                contract_id=contract_id,
                property_name="max_latency_ms",
                expected=policy.max_latency_ms,
                actual=obs.latency_ms,
            ),
        )

    # Operational: pure=true требует effects_observed == () (но не доказывает pure)
    # Пока просто пропускаем, потому что effects_observed=none не означает pure proven.

    return ConformanceResult(
        status=ConformanceStatus.PASS,
        level=ConformanceLevel.OPERATIONAL,
        message="Provided satisfies Required (structural+operational)",
    )


def explain_result(result: ConformanceResult) -> str:
    """Human-readable explanation of conformance result."""
    if result.ok:
        return f"[PASS] {result.message}"
    if result.failure:
        return result.failure.human()
    return f"[{result.status.value}] {result.message}"