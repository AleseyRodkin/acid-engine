from acid_engine.level2.conformance import check_conformance
from acid_engine.level2.semantic import check_semantic
from acid_engine.level2.specification import Policy
from acid_engine.level3.container.observation import ExecutionObservation


def test_invariant_predicate_pass():
    def inv(x):
        return x > 0
    assert check_semantic("invariant", 5, inv)[0]

def test_invariant_predicate_fail():
    def inv(x):
        return x > 10
    assert not check_semantic("invariant", 5, inv)[0]

def test_conformance_with_invariants():
    obs = ExecutionObservation.create(0, 0.001, "completed")
    result = check_conformance(
        "int", 42, obs, Policy(),
        invariants=(lambda x: x > 0, lambda x: x % 2 == 0),
    )
    assert result.ok

def test_conformance_invariant_violation():
    obs = ExecutionObservation.create(0, 0.001, "completed")
    result = check_conformance(
        "int", -5, obs, Policy(),
        invariants=(lambda x: x > 0,),
    )
    assert not result.ok
    assert "invariant" in result.message