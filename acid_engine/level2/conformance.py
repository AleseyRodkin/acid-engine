"""Conformance levels and result types."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from acid_engine.level2.failure import FailureReason
from acid_engine.level2.semantic import check_semantic
from acid_engine.level2.specification import Policy
from acid_engine.level3.container.observation import ExecutionObservation


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
    failure: FailureReason | None = None

    @property
    def ok(self) -> bool:
        return self.status == ConformanceStatus.PASS

    @staticmethod
    def skipped(message: str, level: ConformanceLevel = ConformanceLevel.STRUCTURAL) -> ConformanceResult:
        """No observation — not PASS. Facts were insufficient to judge."""
        return ConformanceResult(
            status=ConformanceStatus.SKIPPED,
            level=level,
            message=message,
        )


_KNOWN_OUTPUT_TYPES = frozenset(
    {"int", "bool", "float", "str", "list", "dict", "record", "None"}
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
    return False


def check_conformance(
    required_output_type: str,
    provided_data: Any,
    obs: ExecutionObservation,
    policy: Policy,
    node_id: str = "",
    contract_id: str = "",
    schema: Any = None,
    semantic_rules: dict[str, Any] | None = None,
    invariants: tuple[Any, ...] | None = None,
) -> ConformanceResult:
    # No completed — no right to PASS. Do not mask failed/skipped with a type-check.
    if obs.status == "skipped":
        return ConformanceResult.skipped("execution was skipped")
    if obs.status != "completed":
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.OPERATIONAL,
            message="execution did not complete",
            failure=FailureReason(
                node_id=node_id,
                contract_id=contract_id,
                property_name="status",
                expected="completed",
                actual=obs.status,
            ),
        )

    kind = (required_output_type or "").strip()
    if kind not in _KNOWN_OUTPUT_TYPES:
        return ConformanceResult.skipped("output_type not in the type dictionary")

    # Structural check — bool ≠ int
    if not _type_matches(kind, provided_data):
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message="Output type mismatch",
            failure=FailureReason(
                node_id=node_id,
                contract_id=contract_id,
                property_name="output_type",
                expected=kind,
                actual=type(provided_data).__name__,
            ),
        )

    # Record schema
    if kind == "record" and schema is not None:
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

    # Property-based invariants (if passed)
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
    # pure=True + observed effects → FAIL (Observed ≠ claim of purity)
    if policy.pure and obs.effects_observed:
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.OPERATIONAL,
            message="pure policy violated: effects observed",
            failure=FailureReason(
                node_id=node_id,
                contract_id=contract_id,
                property_name="pure",
                expected=True,
                actual=list(obs.effects_observed),
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
    line = f"[{result.status.value}] {result.message}"
    if result.status == ConformanceStatus.SKIPPED:
        from acid_engine.evidence import missing_evidence

        gaps = missing_evidence(result)
        line += "\nMissing evidence: " + ", ".join(gaps)
        line += "\nNot enough facts to verify."
    return line


def explain_block(result: ConformanceResult) -> str:
    """Why blocked, then the machine line. SKIPPED stays a skip, not a block."""
    if result.ok or result.failure is None:
        return explain_result(result)
    fail = result.failure
    prop = fail.property_name
    if prop == "source_hash":
        why = (
            "Execution blocked\n"
            "The tool file bytes do not match the lock (source_hash).\n"
            "The file was not imported."
        )
    elif prop == "module_hash":
        why = (
            "Execution blocked\n"
            "The locked tool body does not match the file on disk (module_hash).\n"
            "The body was not executed."
        )
    elif prop == "runtime_hash":
        name = fail.detail or "a contour file"
        if str(fail.actual) == "missing":
            why = (
                "Execution blocked\n"
                "runtime_hashes missing from the lock.\n"
                "The body was not executed."
            )
        else:
            why = (
                "Execution blocked\n"
                f"{name} differs from the approved contour (runtime_hash).\n"
                "The body was not executed."
            )
    elif prop == "worker_hash":
        if str(fail.actual) == "missing":
            why = (
                "Execution blocked\n"
                "worker_hash missing from the lock.\n"
                "The body was not executed."
            )
        else:
            why = (
                "Execution blocked\n"
                "worker.py differs from the approved contour (worker_hash).\n"
                "The body was not executed."
            )
    elif prop == "python_version":
        why = (
            "Execution blocked\n"
            f"lock taken on CPython {fail.expected}, running {fail.actual} — re-take the lock.\n"
            "The body was not executed."
        )
    elif prop == "canon_kind":
        why = (
            "Execution blocked\n"
            f"lock taken with canon_kind {fail.expected}, running {fail.actual} — re-take the lock.\n"
            "The body was not executed."
        )
    elif prop == "dependency_hash":
        why = (
            "Execution blocked\n"
            f"A local import of the tool differs from the lock ({fail.detail or 'dependency_hash'}).\n"
            "The body was not executed."
        )
    elif prop == "output_type":
        why = (
            "Observation did not satisfy the contract\n"
            f"Expected {fail.expected}, got {fail.actual} (output_type). "
            "bool is not int.\n"
            "The body ran; this is not a proof of safety."
        )
    elif prop == "pure":
        why = (
            "Observation did not satisfy the contract\n"
            "declared_pure (Policy.pure) but effects were observed. "
            "Runtime does not instrument I/O; empty effects still do not prove purity.\n"
            "The body ran; this is not proven_pure."
        )
    elif prop == "max_latency_ms":
        why = (
            "Observation did not satisfy the contract\n"
            f"Latency {fail.actual} ms exceeded max_latency_ms {fail.expected}.\n"
            "The body ran."
        )
    elif prop == "status":
        why = (
            "Observation did not satisfy the contract\n"
            f"The body ran and did not complete (status {fail.actual}).\n"
            "This is not a pre-run block."
        )
    else:
        why = f"Execution blocked\n{fail.human()}\nThe body was not executed."
    return why + "\n" + fail.human()