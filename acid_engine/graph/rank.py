"""Compute dependency rank for nodes (assuming DAG)."""
from __future__ import annotations

from typing import Dict
from acid_engine.graph.model import DependencyGraph


def compute_rank(graph: DependencyGraph) -> Dict[str, int]:
    """
    rank(node) = 0 if no deps else 1 + max(rank(deps))
    Assumes DAG (call detect_cycle first).
    """
    ranks: Dict[str, int] = {}

    def rank_of(n: str) -> int:
        if n in ranks:
            return ranks[n]
        preds = graph.predecessors(n)
        if not preds:
            ranks[n] = 0
        else:
            ranks[n] = 1 + max(rank_of(p) for p in preds)
        return ranks[n]

    for node_id in graph.nodes:
        rank_of(node_id)
    return ranks