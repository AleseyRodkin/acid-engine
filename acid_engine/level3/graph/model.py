"""Graph model."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class GraphNode:
    node_id: str
    payload: object = None  # ScriptModule / Module reference


@dataclass
class GraphEdge:
    source: str
    target: str


@dataclass
class DependencyGraph:
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)

    def add_node(self, node_id: str, payload: object = None) -> None:
        self.nodes[node_id] = GraphNode(node_id=node_id, payload=payload)

    def add_edge(self, source: str, target: str) -> None:
        self.edges.append(GraphEdge(source=source, target=target))

    def successors(self, node_id: str) -> List[str]:
        return [e.target for e in self.edges if e.source == node_id]

    def predecessors(self, node_id: str) -> List[str]:
        return [e.source for e in self.edges if e.target == node_id]