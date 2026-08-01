import pytest
from acid_engine.contracts.resolver import ConstraintResolver, ResolveConflict


def test_max_latency_min_merge():
    r = ConstraintResolver()
    assert r.resolve_field("max_latency_ms", 100, 50) == 50

def test_max_latency_parent_none():
    r = ConstraintResolver()
    assert r.resolve_field("max_latency_ms", None, 50) == 50

def test_max_latency_child_none():
    r = ConstraintResolver()
    assert r.resolve_field("max_latency_ms", 100, None) == 100

def test_quality_gate_max_merge():
    r = ConstraintResolver()
    assert r.resolve_field("quality_gate", 0.8, 0.9) == 0.9

def test_allowed_domains_intersection():
    r = ConstraintResolver()
    assert r.resolve_field("allowed_domains", ["A", "B"], ["B", "C"]) == ["B"]

def test_forbidden_effects_union():
    r = ConstraintResolver()
    assert r.resolve_field("forbidden_effects", ["write"], ["delete"]) == ["delete", "write"]

def test_pure_strengthen():
    r = ConstraintResolver()
    assert r.resolve_field("pure", False, True) is True

def test_pure_conflict():
    r = ConstraintResolver()
    with pytest.raises(ResolveConflict):
        r.resolve_field("pure", True, False)

def test_pure_no_conflict_false_false():
    r = ConstraintResolver()
    assert r.resolve_field("pure", False, False) is False

def test_fallback_no_strategy():
    r = ConstraintResolver()
    # нет стратегии: child wins
    assert r.resolve_field("some_field", "parent", "child") == "child"
    assert r.resolve_field("some_field", None, "child") == "child"
    assert r.resolve_field("some_field", "parent", None) == "parent"

def test_resolve_policy():
    r = ConstraintResolver()
    parent = {"max_latency_ms": 100, "pure": True}
    child = {"max_latency_ms": 50}
    result = r.resolve_policy(parent, child)
    assert result["max_latency_ms"] == 50
    assert result["pure"] is True