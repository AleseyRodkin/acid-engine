"""CompositeModule — модуль, состоящий из графа подмодулей."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.graph.cycle import detect_cycle
from acid_engine.level3.graph.rank import compute_rank
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.script.python_runtime import run_script


@dataclass(frozen=True, slots=True)
class CompositeModule:
    """Модуль, реализованный как граф модулей (Leaf или Composite)."""
    module_id: str
    graph: DependencyGraph
    modules: Dict[str, Any]          # node_id -> LeafModule или CompositeModule
    contract_id: ContractId
    version: Version
    input_node: str                  # узел, с которого начинается выполнение
    output_node: str                 # узел, результат которого возвращается

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

    def execute(self, input_data: Any) -> Any:
        import asyncio
        from acid_engine.level3.script.async_module import AsyncScriptModule
        from acid_engine.level3.script.async_runtime import run_async_script

        if detect_cycle(self.graph) is not None:
            raise RuntimeError("Cycle detected in composite module graph")

        ranks = compute_rank(self.graph)
        sorted_nodes = sorted(self.graph.nodes.keys(), key=lambda n: ranks[n])

        node_outputs: Dict[str, Any] = {}
        current_data = input_data

        for node_id in sorted_nodes:
            mod = self.modules[node_id]
            preds = self.graph.predecessors(node_id)
            if not preds:
                input_val = current_data
            else:
                input_val = node_outputs[preds[0]]

            # Выполняем модуль в зависимости от его типа
            if isinstance(mod, LeafModule):
                in_port = PortRef(module=node_id, direction="input", name="value")
                input_snap = ContainerSnapshot.create(
                    port_ref=in_port,
                    contract_id=mod.contract_id,
                    contract_hash=mod.content_hash,
                    data=input_val,
                )
                # Если скрипт — асинхронный, запускаем через asyncio
                if isinstance(mod.script, AsyncScriptModule):
                    out_snap, _, _, _ = asyncio.run(
                        run_async_script(mod.script, input_snap)
                    )
                else:
                    from acid_engine.level3.script.python_runtime import run_script
                    out_snap, _, _, _ = run_script(mod.script, input_snap)
                node_outputs[node_id] = out_snap.data

            elif isinstance(mod, CompositeModule):
                node_outputs[node_id] = mod.execute(input_val)
            else:
                raise TypeError(f"Unknown module type for node {node_id}")

        return node_outputs[self.output_node]