"""Conformance levels and result types."""
from __future__ import annotations

from typing import Any, Optional
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional
from acid_engine.level2.failure import FailureReason
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level2.specification import Policy
from acid_engine.level2.semantic import check_semantic


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

    @staticmethod
    def skipped(message: str, level: ConformanceLevel = ConformanceLevel.STRUCTURAL) -> "ConformanceResult":
        """No observation — not PASS. Facts were insufficient to judge."""
        return ConformanceResult(
            status=ConformanceStatus.SKIPPED,
            level=level,
            message=message,
        )


def _type_matches(required: str, value: Any) -> bool:
    """Structural type check. bool is not int (unlike isinstance)."""
    if required == "int":
        return type(value) is int
    if required == "bool":
        return type(value) is bool
    if required == "float":
        return type(value) in (int, float) and type(value) is not bool
    if required == "str":
        return type(value) is str
    if required == "list":
        return type(value) is list
    if required in ("dict", "record"):
        return type(value) is dict
    if required == "None":
        return value is None
    return True


def check_conformance(
    required_output_type: str,
    provided_data: Any,
    obs: ExecutionObservation,
    policy: Policy,
    node_id: str = "",
    contract_id: str = "",
    schema: Any = None,
    semantic_rules: Optional[dict[str, Any]] = None,
    invariants: Optional[tuple] = None,
) -> ConformanceResult:
    # Structural check — bool ≠ int
    if not _type_matches(required_output_type, provided_data):
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

    # Record schema
    if required_output_type == "record" and schema is not None:
        from acid_engine.level3.container.types import RecordSchema
        if isinstance(schema, RecordSchema):
            ok, _ = schema.validate(provided_data, apply_defaults=True)
            if not ok:
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

    # Semantic rules (NEW)
    if semantic_rules:
        from acid_engine.level2.semantic import check_semantic_rules
        results = check_semantic_rules(semantic_rules, provided_data)
        for ok, pred_name, msg in results:
            if not ok:
                return ConformanceResult(
                    status=ConformanceStatus.FAIL,
                    level=ConformanceLevel.SEMANTIC,
                    message=f"Semantic rule '{pred_name}' failed: {msg}",
                    failure=FailureReason(
                        node_id=node_id,
                        contract_id=contract_id,
                        property_name=pred_name,
                        expected=str(semantic_rules[pred_name]),
                        actual=str(provided_data),
                    ),
                )

    # Проверка Property-Based инвариантов (если переданы)
    if invariants:
        for inv in invariants:
            ok, msg = check_semantic("invariant", provided_data, inv)
            if not ok:
                return ConformanceResult(
                    status=ConformanceStatus.FAIL,
                    level=ConformanceLevel.SEMANTIC,
                    message=f"Property invariant violated: {msg}",
                    failure=FailureReason(
                        node_id=node_id,
                        contract_id=contract_id,
                        property_name="invariant",
                        expected="True",
                        actual=msg,
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