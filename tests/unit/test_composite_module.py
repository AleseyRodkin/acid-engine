import pytest
from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.module.composite import CompositeModule, CompositeResult
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import lock_for_script


def make_leaf(name: str, func) -> LeafModule:
    script = ScriptModule(
        contract_id=ContractId("test", name),
        version=Version(1, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=func,
        name=name,
    )
    return LeafModule(module_id=name, script=script)


def test_composite_with_one_node():
    leaf = make_leaf("x2", lambda x: x * 2)
    g = DependencyGraph()
    g.add_node("x2", payload=leaf)
    composite = CompositeModule(
        module_id="comp",
        graph=g,
        modules={"x2": leaf},
        contract_id=ContractId("test", "comp"),
        version=Version(1, 0, 0),
        input_node="x2",
        output_node="x2",
    )
    result = composite.execute(5)
    assert isinstance(result, CompositeResult)
    assert result.ok
    assert result.data == 10
    assert result.observation is not None
    assert result.observation.status == "completed"
    assert len(result.observations) == 1


def test_composite_two_nodes():
    leaf_a = make_leaf("plus1", lambda x: x + 1)
    leaf_b = make_leaf("times2", lambda x: x * 2)
    g = DependencyGraph()
    g.add_node("plus1", payload=leaf_a)
    g.add_node("times2", payload=leaf_b)
    g.add_edge("plus1", "times2")
    composite = CompositeModule(
        module_id="pipe",
        graph=g,
        modules={"plus1": leaf_a, "times2": leaf_b},
        contract_id=ContractId("test", "pipe"),
        version=Version(1, 0, 0),
        input_node="plus1",
        output_node="times2",
    )
    result = composite.execute(3)
    assert result.ok
    assert result.data == 8
    assert len(result.observations) == 2
    assert all(o.status == "completed" for o in result.observations)


def test_composite_with_cycle():
    leaf = make_leaf("id", lambda x: x)
    g = DependencyGraph()
    g.add_node("a", payload=leaf)
    g.add_node("b", payload=leaf)
    g.add_edge("a", "b")
    g.add_edge("b", "a")
    composite = CompositeModule(
        module_id="cycle",
        graph=g,
        modules={"a": leaf, "b": leaf},
        contract_id=ContractId("test", "cycle"),
        version=Version(1, 0, 0),
        input_node="a",
        output_node="b",
    )
    with pytest.raises(RuntimeError, match="[Cc]ycle"):
        composite.execute(1)


def test_composite_fan_in_forbidden():
    leaf_a = make_leaf("a", lambda x: x + 1)
    leaf_b = make_leaf("b", lambda x: x * 2)
    leaf_c = make_leaf("c", lambda x: x)
    g = DependencyGraph()
    g.add_node("a", payload=leaf_a)
    g.add_node("b", payload=leaf_b)
    g.add_node("c", payload=leaf_c)
    g.add_edge("a", "c")
    g.add_edge("b", "c")
    composite = CompositeModule(
        module_id="fan",
        graph=g,
        modules={"a": leaf_a, "b": leaf_b, "c": leaf_c},
        contract_id=ContractId("test", "fan"),
        version=Version(1, 0, 0),
        input_node="a",
        output_node="c",
    )
    with pytest.raises(RuntimeError, match="Fan-in"):
        composite.execute(5)


def test_composite_external_plan_rejects_swapped_leaf():
    good = make_leaf("plus1", lambda x: x + 1)
    called = []

    def swapped(x):
        called.append(x)
        return x + 100

    bad = make_leaf("plus1", swapped)
    g = DependencyGraph()
    g.add_node("plus1", payload=bad)
    composite = CompositeModule(
        module_id="pipe",
        graph=g,
        modules={"plus1": bad},
        contract_id=ContractId("test", "pipe"),
        version=Version(1, 0, 0),
        input_node="plus1",
        output_node="plus1",
    )
    iface, plan = lock_for_script(good.script)
    result = composite.execute(1, plan=plan, iface=iface)
    assert not result.ok
    assert result.status is not None
    assert result.data is None
    assert called == []


def test_composite_plan_without_iface_does_not_run():
    called = []

    def f(x):
        called.append(x)
        return x

    leaf = make_leaf("id", f)
    g = DependencyGraph()
    g.add_node("id", payload=leaf)
    composite = CompositeModule(
        module_id="c",
        graph=g,
        modules={"id": leaf},
        contract_id=ContractId("test", "c"),
        version=Version(1, 0, 0),
        input_node="id",
        output_node="id",
    )
    _iface, plan = lock_for_script(leaf.script)
    result = composite.execute(1, plan=plan, iface=None)
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert result.data is None
    assert called == []
