"""CompositeModule — модуль, состоящий из графа подмодулей."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
from acid_engine.graph.model import DependencyGraph
from acid_engine.graph.cycle import detect_cycle
from acid_engine.graph.rank import compute_rank
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.contracts.serialization import content_hash_of
from acid_engine.modules.leaf import LeafModule
from acid_engine.containers.port import PortRef
from acid_engine.containers.snapshot import ContainerSnapshot
from acid_engine.scripts.python_runtime import run_script


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
        """
        Выполняет граф модулей.
        Предполагается, что граф — DAG, и каждый модуль имеет один вход и выход.
        """
        # Проверка на циклы
        if detect_cycle(self.graph) is not None:
            raise RuntimeError("Cycle detected in composite module graph")

        # Вычисляем ранги и сортируем узлы по рангу
        ranks = compute_rank(self.graph)
        sorted_nodes = sorted(self.graph.nodes.keys(), key=lambda n: ranks[n])

        # Храним выходные данные узлов
        node_outputs: Dict[str, Any] = {}

        # Начальные данные подаются на входной узел
        current_data = input_data

        for node_id in sorted_nodes:
            mod = self.modules[node_id]
            # Определяем, откуда брать входные данные
            preds = self.graph.predecessors(node_id)
            if not preds:
                # Входной узел — используем переданные данные
                input_val = current_data
            else:
                # Если предшественник один — берём его выход
                # (для простоты предполагаем один вход)
                pred = preds[0]
                input_val = node_outputs[pred]

            # Выполняем модуль
            if isinstance(mod, LeafModule):
                in_port = PortRef(module=node_id, direction="input", name="value")
                input_snap = ContainerSnapshot.create(
                    port_ref=in_port,
                    contract_id=mod.contract_id,
                    contract_hash=mod.content_hash,
                    data=input_val,
                )
                out_snap, _, _, _ = run_script(mod.script, input_snap)
                node_outputs[node_id] = out_snap.data
            elif isinstance(mod, CompositeModule):
                node_outputs[node_id] = mod.execute(input_val)
            else:
                raise TypeError(f"Unknown module type for node {node_id}")

        return node_outputs[self.output_node]