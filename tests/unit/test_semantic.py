import pytest
from acid_engine.level2.semantic import (
    check_semantic, check_semantic_rules,
)
from acid_engine.level2.conformance import check_conformance
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.script.specification import Policy


def test_equals():
    assert check_semantic("equals", 42, 42)[0]

def test_contains_string():
    assert check_semantic("contains", "hello world", "world")[0]

def test_matches():
    assert check_semantic("matches", "abc123", r"\d+")[0]

def test_cardinality():
    assert check_semantic("cardinality", [1,2,3], ">=2")[0]

def test_json_schema():
    rules = {"name": {"type": "str"}, "age": {"type": "int"}}
    assert check_semantic("json_schema", {"name": "A", "age": 30}, rules)[0]

def test_conformance_semantic_pass():
    obs = ExecutionObservation.create(0, 0.001, "completed")
    result = check_conformance(
        "int", 42, obs, Policy(),
        semantic_rules={"equals": 42},
    )
    assert result.ok

def test_conformance_semantic_fail():
    obs = ExecutionObservation.create(0, 0.001, "completed")
    result = check_conformance(
        "int", 42, obs, Policy(),
        semantic_rules={"equals": 99},
    )
    assert not result.ok
    assert result.failure.property_name == "equals"

def test_jsonpath_equals():
    data = {"stdout": "hello", "stderr": ""}
    assert check_semantic("jsonpath", data, "$.stdout==hello")[0]

def test_jsonpath_not_found():
    data = {"stdout": "bye"}
    assert not check_semantic("jsonpath", data, "$.stderr==error")[0]

def test_jsonpath_nested():
    data = {"result": {"name": "Alice", "items": [10, 20]}}
    assert check_semantic("jsonpath", data, {"path": "result.name", "value": "Alice", "op": "equals"})[0]
    assert check_semantic("jsonpath", data, {"path": "result.items[0]", "value": "10", "op": "contains"})[0]