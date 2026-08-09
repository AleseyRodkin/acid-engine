import pytest
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.module.composite import CompositeModule
from acid_engine.level3.graph.model import DependencyGraph


def make_leaf(name: str, func) -> LeafModule:
    script = ScriptModule(
        contract_id=ContractId("test", name),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=func,
        name=name,
    )
    return LeafModule(module_id=name, script=script)


def test_composite_with_one_node():
    """Один модуль в композите эквивалентен LeafModule."""
    leaf = make_leaf("x2", lambda x: x * 2)
    g = DependencyGraph()
    g.add_node("x2", payload=leaf)
    composite = CompositeModule(
        module_id="comp",
        graph=g,
        modules={"x2": leaf},
        contract_id=ContractId("test", "comp"),
        version=Version(1,0,0),
        input_node="x2",
        output_node="x2",
    )
    result = composite.execute(5)
    assert result == 10


def test_composite_two_nodes():
    """Два модуля: A (x+1) -> B (x*2). 3 -> 8."""
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
        version=Version(1,0,0),
        input_node="plus1",
        output_node="times2",
    )
    result = composite.execute(3)
    assert result == 8


def test_composite_with_cycle():
    """Граф с циклом должен выбрасывать ошибку при выполнении."""
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
        version=Version(1,0,0),
        input_node="a",
        output_node="b",
    )
    with pytest.raises(RuntimeError, match="[Cc]ycle"):
        composite.execute(1)