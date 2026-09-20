"""Semantic predicates for checking output values."""
from __future__ import annotations

import re
import subprocess
import sys
from typing import Any

_MATCH_BUDGET_S = 0.08


class SemanticPredicate:
    """Base predicate class."""

    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        """Return (passed, message)."""
        raise NotImplementedError


class EqualsPredicate(SemanticPredicate):
    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        if provided == expected:
            return True, "equals"
        return False, f"Expected {expected!r}, got {provided!r}"


class ContainsPredicate(SemanticPredicate):
    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        if isinstance(provided, str):
            if expected in provided:
                return True, "contains"
            return False, f"'{expected}' not found in output"
        if isinstance(provided, (dict, list)):
            import json
            as_str = json.dumps(provided, ensure_ascii=False)
            if expected in as_str:
                return True, "contains"
            return False, f"'{expected}' not found in output"
        if expected in str(provided):
            return True, "contains"
        return False, f"'{expected}' not found in {provided!r}"


class MatchesPredicate(SemanticPredicate):
    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        pattern = str(expected)
        text = str(provided)
        try:
            re.compile(pattern)
        except re.error as e:
            return False, f"invalid pattern: {e}"
        # CPython `re` holds the GIL; a thread join cannot enforce the budget.
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import re,sys; sys.stdout.write('1' if re.search(sys.argv[1], sys.argv[2]) else '0')",
                    pattern,
                    text,
                ],
                capture_output=True,
                text=True,
                timeout=_MATCH_BUDGET_S,
            )
        except subprocess.TimeoutExpired:
            return False, "matches timeout"
        if proc.returncode != 0:
            err = (proc.stderr or "").strip() or f"exit {proc.returncode}"
            return False, f"matches raised: {err}"
        if proc.stdout.strip() == "1":
            return True, f"matches /{pattern}/"
        return False, f"Pattern /{pattern}/ not found in '{text[:80]}...'"


class CardinalityPredicate(SemanticPredicate):
    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        spec = str(expected)
        op = spec[:2] if spec[:2] in (">=", "<=", "==") else spec[:1]
        n = int(spec[len(op) :])
        count = len(provided) if isinstance(provided, (list, dict, str)) else 1
        if op == ">=" and count >= n:
            return True, f"cardinality >= {n}"
        if op == "<=" and count <= n:
            return True, f"cardinality <= {n}"
        if op == "==" and count == n:
            return True, f"cardinality == {n}"
        if op == ">" and count > n:
            return True, f"cardinality > {n}"
        if op == "<" and count < n:
            return True, f"cardinality < {n}"
        return False, f"Cardinality {count} does not satisfy {expected}"


class JsonSchemaPredicate(SemanticPredicate):
    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        if not isinstance(provided, dict):
            return False, "Provided is not a dict"
        if not isinstance(expected, dict):
            return False, "Expected schema is not a dict"
        errors = []
        for key, spec in expected.items():
            if key not in provided:
                if spec.get("required", True):
                    errors.append(f"Missing required field '{key}'")
                continue
            val = provided[key]
            typ = spec.get("type")
            if typ == "int" and not isinstance(val, int):
                errors.append(f"Field '{key}': expected int, got {type(val).__name__}")
            elif typ == "float" and not isinstance(val, (int, float)):
                errors.append(f"Field '{key}': expected float, got {type(val).__name__}")
            elif typ == "str" and not isinstance(val, str):
                errors.append(f"Field '{key}': expected str, got {type(val).__name__}")
            elif typ == "bool" and not isinstance(val, bool):
                errors.append(f"Field '{key}': expected bool, got {type(val).__name__}")
        if errors:
            return False, "; ".join(errors)
        return True, "json_schema valid"


class JsonPathPredicate(SemanticPredicate):
    """Check a JSON field by path (e.g. $.stdout or result.name)."""

    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        if isinstance(expected, str) and "==" in expected:
            path, val = expected.split("==", 1)
            path = path.strip()
            val = val.strip()
            op = "equals"
        elif isinstance(expected, dict):
            path = expected.get("path", "")
            val = expected.get("value", "")
            op = expected.get("op", "equals")
        else:
            return False, "Invalid jsonpath format"

        if path.startswith("$."):
            path = path[2:]
        elif path.startswith("$"):
            path = path[1:]

        extracted = self._extract(provided, path)
        if extracted is None:
            return False, f"Path '{path}' not found"
        if op == "equals":
            if str(extracted) == val:
                return True, f"$.{path} == {val}"
            return False, f"Expected {val}, got {extracted}"
        if op == "contains":
            if val in str(extracted):
                return True, f"$.{path} contains {val}"
            return False, f"Value '{val}' not found in {extracted}"
        return False, f"Unknown op {op}"

    def _extract(self, data: Any, path: str) -> Any:
        parts = path.split(".")
        current = data
        for part in parts:
            if current is None:
                return None
            if "[" in part and part.endswith("]"):
                field, idx_str = part.split("[", 1)
                idx = int(idx_str[:-1])
                if isinstance(current, dict) and field in current:
                    current = current[field]
                else:
                    return None
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current


class InvariantPredicate(SemanticPredicate):
    """Run the given invariant function on provided_data."""

    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        if not callable(expected):
            return False, "Invariant must be callable"
        try:
            result = expected(provided)
            if result:
                return True, "invariant holds"
            return False, "invariant violated"
        except Exception as e:
            return False, f"Invariant check raised: {e}"


PREDICATES: dict[str, SemanticPredicate] = {
    "equals": EqualsPredicate(),
    "contains": ContainsPredicate(),
    "matches": MatchesPredicate(),
    "cardinality": CardinalityPredicate(),
    "json_schema": JsonSchemaPredicate(),
    "jsonpath": JsonPathPredicate(),
    "invariant": InvariantPredicate(),
}


def check_semantic(
    predicate_name: str,
    provided: Any,
    expected: Any,
) -> tuple[bool, str]:
    """
    Check provided against expected with a named predicate.
    Returns (passed, message). Exceptions are FAIL, not raised.
    """
    pred = PREDICATES.get(predicate_name)
    if pred is None:
        return False, f"Unknown predicate: {predicate_name}"
    try:
        return pred.check(provided, expected)
    except Exception as e:
        return False, f"{predicate_name} raised: {e}"


def check_semantic_rules(
    rules: dict[str, Any],
    provided_data: Any,
) -> list[tuple[bool, str, str]]:
    """
    Apply a set of rules: {"predicate_name": expected_value, ...}
    Returns a list of (passed, predicate_name, message).
    """
    results = []
    for pred_name, expected in rules.items():
        ok, msg = check_semantic(pred_name, provided_data, expected)
        results.append((ok, pred_name, msg))
    return results
