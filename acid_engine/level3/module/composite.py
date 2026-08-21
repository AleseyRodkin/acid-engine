"""CompositeModule — модуль, состоящий из графа подмодулей."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.graph.cycle import detect_cycle
from acid_engine.level3.graph.rank import compute_rank
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.script.python_runtime import run_script


@dataclass(frozen=True, slots=True)
class CompositeResult:
    """Факт прогона графа: выход и наблюдения по узлам в порядке исполнения."""

    data: Any
    observations: tuple[ExecutionObservation, ...] = ()

    @property
    def observation(self) -> Optional[ExecutionObservation]:
        return self.observations[-1] if self.observations else None


@dataclass(frozen=True, slots=True)
class CompositeModule:
    """Модуль, реализованный как граф модулей (Leaf или Composite)."""
    module_id: str
    graph: DependencyGraph
    modules: Dict[str, Any]
    contract_id: ContractId
    version: Version
    input_node: str
    output_node: str

    @property
    def content_hash(self) -> str:
        return content_hash_of(self.to_canonical_dict())

    def to_canonical_dict(self) -> dict:
        return {
            "kind": "composite",
            "module_id": self.module_id,
            "contract_id": str(self.contract_id),
            "version": str(self.version),
            "nodes": list(self.graph.nodes.keys()),
            "edges": [
                {"source": e.source, "target": e.target}
                for e in self.graph.edges
            ],
            "input_node": self.input_node,
            "output_node": self.output_node,
        }

    def execute(self, input_data: Any) -> CompositeResult:
        import asyncio
        from acid_engine.level3.script.async_module import AsyncScriptModule
        from acid_engine.level3.script.async_runtime import run_async_script

        if detect_cycle(self.graph) is not None:
            raise RuntimeError("Cycle detected in composite module graph")

        ranks = compute_rank(self.graph)
        sorted_nodes = sorted(self.graph.nodes.keys(), key=lambda n: ranks[n])

        node_outputs: Dict[str, Any] = {}
        observations: list[ExecutionObservation] = []
        current_data = input_data

        for node_id in sorted_nodes:
            mod = self.modules[node_id]
            preds = self.graph.predecessors(node_id)
            if not preds:
                input_val = current_data
            elif len(preds) == 1:
                input_val = node_outputs[preds[0]]
            else:
                raise RuntimeError(
                    f"Fan-in > 1 is not supported for node {node_id!r} "
                    f"(predecessors={preds}). Provide a merge contract first."
                )

            if isinstance(mod, LeafModule):
                in_port = PortRef(module=node_id, direction="input", name="value")
                input_snap = ContainerSnapshot.create(
                    port_ref=in_port,
                    contract_id=mod.contract_id,
                    contract_hash=mod.content_hash,
                    data=input_val,
                )
                if isinstance(mod.script, AsyncScriptModule):
                    out_snap, obs, _, _ = asyncio.run(
                        run_async_script(mod.script, input_snap)
                    )
                else:
                    out_snap, obs, _, _ = run_script(mod.script, input_snap)
                node_outputs[node_id] = out_snap.data
                observations.append(obs)

            elif isinstance(mod, CompositeModule):
                nested = mod.execute(input_val)
                node_outputs[node_id] = nested.data
                observations.extend(nested.observations)
            else:
                raise TypeError(f"Unknown module type for node {node_id}")

        return CompositeResult(
            data=node_outputs[self.output_node],
            observations=tuple(observations),
        )
