"""Cycle detection in dependency graph."""
from __future__ import annotations

from typing import List, Optional
from acid_engine.graph.model import DependencyGraph


def detect_cycle(graph: DependencyGraph) -> Optional[List[str]]:
    """DFS cycle detection. Returns cycle path or None."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph.nodes}
    parent = {n: None for n in graph.nodes}

    def dfs(u: str) -> Optional[List[str]]:
        color[u] = GRAY
        for v in graph.successors(u):
            if color[v] == GRAY:
                cycle = [v, u]
                x = u
                while x != v:
                    x = parent[x]  # type: ignore
                    cycle.append(x)
                cycle.reverse()
                return cycle
            if color[v] == WHITE:
                parent[v] = u
                c = dfs(v)
                if c:
                    return c
        color[u] = BLACK
        return None

    for n in graph.nodes:
        if color[n] == WHITE:
            c = dfs(n)
            if c:
                return c
    return None