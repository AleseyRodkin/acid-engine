"""Property-based tests for ConstraintResolver strategies."""
from hypothesis import given, strategies as st, assume, settings
from acid_engine.level2.resolver import ConstraintResolver, ResolveConflict
from acid_engine.level2.strategies.numeric import MinValueStrategy, MaxValueStrategy
from acid_engine.level2.strategies.set_ops import IntersectionStrategy, UnionStrategy
from acid_engine.level2.strategies.boolean_policy import BooleanStrengthenStrategy


# --- Numeric strategies ---
@given(st.integers(), st.integers())
def test_min_strategy_returns_min(a, b):
    s = MinValueStrategy()
    assert s.merge(a, b) == min(a, b)

@given(st.floats(allow_nan=False, allow_infinity=False), st.floats(allow_nan=False, allow_infinity=False))
def test_min_strategy_float(a, b):
    s = MinValueStrategy()
    assert s.merge(a, b) == min(a, b)

@given(st.integers(), st.integers())
def test_max_strategy_returns_max(a, b):
    s = MaxValueStrategy()
    assert s.merge(a, b) == max(a, b)


# --- Set strategies ---
@given(st.lists(st.integers()), st.lists(st.integers()))
def test_intersection_is_commutative(a, b):
    s = IntersectionStrategy()
    assert sorted(s.merge(a, b)) == sorted(s.merge(b, a))

@given(st.lists(st.integers()), st.lists(st.integers()))
def test_union_is_commutative(a, b):
    s = UnionStrategy()
    assert sorted(s.merge(a, b)) == sorted(s.merge(b, a))

@given(st.lists(st.integers()))
def test_intersection_with_self_is_self(lst):
    s = IntersectionStrategy()
    assert sorted(s.merge(lst, lst)) == sorted(set(lst))

@given(st.lists(st.integers()))
def test_union_with_self_is_self(lst):
    s = UnionStrategy()
    assert sorted(s.merge(lst, lst)) == sorted(set(lst))


# --- Boolean strategy ---
@given(st.booleans(), st.booleans())
def test_boolean_strengthen_merge(parent, child):
    s = BooleanStrengthenStrategy()
    # effective = parent OR child
    assert s.merge(parent, child) == (parent or child)

@given(st.booleans(), st.booleans())
def test_boolean_strengthen_compare(parent, child):
    s = BooleanStrengthenStrategy()
    # конфликт: parent=True, child=False
    assert s.detect_conflict(parent, child) == (parent is True and child is False)

@given(st.booleans(), st.booleans())
def test_boolean_strategy_compare_provided_required(provided, required):
    s = BooleanStrengthenStrategy()
    if not required:
        assert s.compare_provided_required(provided, required) is True
    else:
        assert s.compare_provided_required(provided, required) == (provided is True)


# --- Resolver integration ---
@given(st.integers(), st.integers(), st.integers())
def test_resolver_numeric_defaults(parent, child, default):
    assume(parent is not None and child is not None and default is not None)
    resolver = ConstraintResolver()
    # max_latency_ms uses MinValueStrategy, effective = min(parent, child)
    effective = resolver.resolve_field("max_latency_ms", parent, child, default)
    if parent is not None and child is not None:
        assert effective == min(parent, child)
    elif parent is not None:
        assert effective == parent
    elif child is not None:
        assert effective == child
    else:
        assert effective == default

@given(st.lists(st.integers()), st.lists(st.integers()))
def test_resolver_set_intersection(a, b):
    resolver = ConstraintResolver()
    result = resolver.resolve_field("allowed_domains", a, b)
    expected = sorted(set(a or []) & set(b or []))
    assert result == expected

@given(st.booleans(), st.booleans())
def test_resolver_pure_no_conflict(parent, child):
    resolver = ConstraintResolver()
    if parent is True and child is False:
        try:
            resolver.resolve_field("pure", parent, child)
            assert False, "Should have raised ResolveConflict"
        except ResolveConflict:
            pass
    else:
        effective = resolver.resolve_field("pure", parent, child)
        assert effective == (parent or child)

# Проверка, что resolve_policy не меняет размер словаря (ключи сохраняются)
@given(st.dictionaries(
    st.text(min_size=1).filter(lambda k: k not in ConstraintResolver().strategies),
    st.integers(),
))
def test_resolve_policy_keeps_keys(d):
    resolver = ConstraintResolver()
    result = resolver.resolve_policy(d, {})
    assert set(result.keys()) == set(d.keys())