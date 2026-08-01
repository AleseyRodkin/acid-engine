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
    schema: Any = None,  # RecordSchema, если тип record
) -> ConformanceResult:
    """
    Compare Provided against Required.
    """
    # Structural check
    type_map = {
        "int": int,
        "float": (int, float),
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "record": dict,   # record — это dict, проверяем по схеме
        "None": type(None),
    }
    expected = type_map.get(required_output_type, object)
    if not isinstance(provided_data, expected):
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

    # Если record — валидация по схеме
    if required_output_type == "record" and schema is not None:
        from acid_engine.containers.types import RecordSchema
        if isinstance(schema, RecordSchema):
            if not schema.validate(provided_data):
                return ConformanceResult(
                    status=ConformanceStatus.FAIL,
                    level=ConformanceLevel.STRUCTURAL,
                    message="Record schema validation failed",
                    failure=FailureReason(
                        node_id=node_id,
                        contract_id=contract_id,
                        property_name="record_schema",
                        expected=str(schema.to_canonical_dict()),
                        actual=str(provided_data),
                    ),
                )

    # Operational: latency
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