"""Семантические предикаты для проверки выходных значений."""
from __future__ import annotations

import re
import json
from typing import Any, Dict, List, Optional


class SemanticPredicate:
    """Базовый класс предиката."""

    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        """Возвращает (passed, message)."""
        raise NotImplementedError


class EqualsPredicate(SemanticPredicate):
    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        if provided == expected:
            return True, "equals"
        return False, f"Expected {expected!r}, got {provided!r}"


class ContainsPredicate(SemanticPredicate):
    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        # если provided — строка, ищем подстроку
        if isinstance(provided, str):
            if expected in provided:
                return True, "contains"
            return False, f"'{expected}' not found in output"
        # для словаря или списка ищем в JSON-представлении
        if isinstance(provided, (dict, list)):
            import json
            as_str = json.dumps(provided, ensure_ascii=False)
            if expected in as_str:
                return True, "contains"
            return False, f"'{expected}' not found in output"
        # остальные типы
        if expected in str(provided):
            return True, "contains"
        return False, f"'{expected}' not found in {provided!r}"

class MatchesPredicate(SemanticPredicate):
    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        pattern = str(expected)
        text = str(provided)
        if re.search(pattern, text):
            return True, f"matches /{pattern}/"
        return False, f"Pattern /{pattern}/ not found in '{text[:80]}...'"


class CardinalityPredicate(SemanticPredicate):
    def check(self, provided: Any, expected: Any) -> tuple[bool, str]:
        # expected: ">=N", "==N", "<=N"
        op = expected[:2] if expected[:2] in (">=", "<=", "==") else expected[:1]
        n = int(expected[len(op):])
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
        # expected — словарь с простой JSON Schema (поля + типы)
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
    """Проверка JSON-поля по пути (например, $.stdout или result.name)."""

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

        # нормализуем путь: убираем начальный '$' или '$.'
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
        """Извлекает значение по простому пути (без $)."""
        parts = path.split(".")
        current = data
        for part in parts:
            if current is None:
                return None
            # Обработка индексов [n]
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

PREDICATES: Dict[str, SemanticPredicate] = {
    "equals": EqualsPredicate(),
    "contains": ContainsPredicate(),
    "matches": MatchesPredicate(),
    "cardinality": CardinalityPredicate(),
    "json_schema": JsonSchemaPredicate(),
    "jsonpath": JsonPathPredicate(),   # <-- новая строка
}


def check_semantic(
    predicate_name: str,
    provided: Any,
    expected: Any,
) -> tuple[bool, str]:
    """
    Проверяет provided против expected с помощью именованного предиката.
    Возвращает (passed, message).
    """
    pred = PREDICATES.get(predicate_name)
    if pred is None:
        return False, f"Unknown predicate: {predicate_name}"
    return pred.check(provided, expected)


def check_semantic_rules(
    rules: Dict[str, Any],
    provided_data: Any,
) -> list[tuple[bool, str, str]]:
    """
    Применяет набор правил: {"predicate_name": expected_value, ...}
    Возвращает список (passed, predicate_name, message).
    """
    results = []
    for pred_name, expected in rules.items():
        ok, msg = check_semantic(pred_name, provided_data, expected)
        results.append((ok, pred_name, msg))
    return results