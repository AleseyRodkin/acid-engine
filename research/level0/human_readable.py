"""Human-readable view (level 0)."""
from __future__ import annotations

from typing import Any


class HumanReadableView:
    """Render contracts and graphs as text."""

    def render(self, entity: Any) -> str:
        if hasattr(entity, 'contract_id') and hasattr(entity, 'specification'):
            return self._render_script(entity)
        if hasattr(entity, 'nodes') and hasattr(entity, 'edges'):
            return self._render_graph(entity)
        return str(entity)

    def _render_script(self, script: Any) -> str:
        lines = [
            f"=== Script: {script.name or script.contract_id.name} ===",
            "Specification:",
            f"  Input: {script.input_type}",
            f"  Output: {script.output_type}",
            f"  Policy: {script.specification.policy.to_canonical_dict() if hasattr(script.specification, 'policy') else 'none'}",
            "Implementation:",
            f"  (live function {getattr(script.implementation, '__name__', 'lambda')})"
        ]
        return "\n".join(lines)

    def _render_graph(self, graph: Any) -> str:
        from acid_engine.level3.graph.cycle import detect_cycle
        lines = ["=== Graph ==="]
        for edge in graph.edges:
            lines.append(f"  {edge.source} → {edge.target}")
        cycle = detect_cycle(graph)
        if cycle:
            lines.append(f"  WARNING: cycle detected {cycle}")
        return "\n".join(lines)