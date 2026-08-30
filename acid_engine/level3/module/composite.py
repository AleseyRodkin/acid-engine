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
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level2.conformance import ConformanceResult


@dataclass(frozen=True, slots=True)
class CompositeResult:
    """Факт прогона графа: данные, наблюдения, вердикт. Нет conformance — не PASS."""

    data: Any
    observations: tuple[ExecutionObservation, ...] = ()
    conformance: Optional[ConformanceResult] = None

    @property
    def observation(self) -> Optional[ExecutionObservation]:
        return self.observations[-1] if self.observations else None

    @property
    def ok(self) -> bool:
        return bool(self.conformance and self.conformance.ok)

    @property
    def status(self):
        return None if self.conformance is None else self.conformance.status


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

    def execute(
        self,
        input_data: Any,
        plan: Optional[PlanLock] = None,
        iface: Optional[InterfaceContract] = None,
    ) -> CompositeResult:
        import asyncio
        from acid_engine.level2.conformance import check_conformance
        from acid_engine.level3.script.async_module import AsyncScriptModule
        from acid_engine.level3.script.async_runtime import run_async_script
        from acid_engine.level3.script.runner import (
            execute_plan,
            lock_for_script,
            bind_script_to_plan,
        )

        if (plan is None) != (iface is None):
            return CompositeResult(
                data=None,
                observations=(),
                conformance=ConformanceResult.skipped(
                    "plan and iface must be provided together"
                ),
            )

        if detect_cycle(self.graph) is not None:
            raise RuntimeError("Cycle detected in composite module graph")

        ranks = compute_rank(self.graph)
        sorted_nodes = sorted(self.graph.nodes.keys(), key=lambda n: ranks[n])

        node_outputs: Dict[str, Any] = {}
        observations: list[ExecutionObservation] = []
        last_conf: Optional[ConformanceResult] = None
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
                if plan is not None and iface is not None:
                    leaf_iface, leaf_plan = iface, plan
                else:
                    leaf_iface, leaf_plan = lock_for_script(mod.script)
                if isinstance(mod.script, AsyncScriptModule):
                    bound = bind_script_to_plan(leaf_plan, mod.script)
                    if bound is not None:
                        return CompositeResult(
                            data=None,
                            observations=tuple(observations),
                            conformance=bound,
                        )
                    in_port = PortRef(module=node_id, direction="input", name="value")
                    input_snap = ContainerSnapshot.create(
                        port_ref=in_port,
                        contract_id=mod.contract_id,
                        contract_hash=mod.content_hash,
                        data=input_val,
                    )
                    out_snap, obs, _, _ = asyncio.run(
                        run_async_script(mod.script, input_snap)
                    )
                    observations.append(obs)
                    conf = check_conformance(
                        required_output_type=mod.script.output_type,
                        provided_data=out_snap.data,
                        obs=obs,
                        policy=mod.script.specification.policy,
                        node_id=mod.script.name,
                        contract_id=str(mod.script.contract_id),
                    )
                    last_conf = conf
                    if not conf.ok:
                        return CompositeResult(
                            data=None,
                            observations=tuple(observations),
                            conformance=conf,
                        )
                    node_outputs[node_id] = out_snap.data
                else:
                    step = execute_plan(leaf_iface, leaf_plan, mod.script, input_val)
                    if step.observation is not None:
                        observations.append(step.observation)
                    last_conf = step.conformance
                    if not step.ok:
                        return CompositeResult(
                            data=step.data,
                            observations=tuple(observations),
                            conformance=step.conformance,
                        )
                    node_outputs[node_id] = step.data

            elif isinstance(mod, CompositeModule):
                nested = mod.execute(input_val, plan=plan, iface=iface)
                observations.extend(nested.observations)
                last_conf = nested.conformance
                if not nested.ok:
                    return CompositeResult(
                        data=nested.data,
                        observations=tuple(observations),
                        conformance=nested.conformance,
                    )
                node_outputs[node_id] = nested.data
            else:
                raise TypeError(f"Unknown module type for node {node_id}")

        if last_conf is None:
            last_conf = ConformanceResult.skipped("graph had no executed leaves")
        return CompositeResult(
            data=node_outputs[self.output_node],
            observations=tuple(observations),
            conformance=last_conf,
        )
