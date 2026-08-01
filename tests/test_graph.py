import pytest
from acid_engine.graph.model import DependencyGraph
from acid_engine.graph.cycle import detect_cycle
from acid_engine.graph.rank import compute_rank


def test_graph_construction():
    g = DependencyGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_edge("A", "B")
    assert g.successors("A") == ["B"]
    assert g.predecessors("B") == ["A"]
    assert g.successors("B") == []

def test_cycle_detection_no_cycle():
    g = DependencyGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_edge("A", "B")
    assert detect_cycle(g) is None

def test_cycle_detection_with_cycle():
    g = DependencyGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_edge("A", "B")
    g.add_edge("B", "A")
    cycle = detect_cycle(g)
    assert cycle is not None
    assert "A" in cycle and "B" in cycle

def test_rank():
    g = DependencyGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_node("C")
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    ranks = compute_rank(g)
    assert ranks["A"] == 0
    assert ranks["B"] == 1
    assert ranks["C"] == 2

def test_rank_with_diamond():
    g = DependencyGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_node("C")
    g.add_node("D")
    g.add_edge("A", "B")
    g.add_edge("A", "C")
    g.add_edge("B", "D")
    g.add_edge("C", "D")
    ranks = compute_rank(g)
    assert ranks["A"] == 0
    assert ranks["D"] == 2
    assert ranks["B"] == 1
    assert ranks["C"] == 1