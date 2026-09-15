"""CompositeModule — a module made of a graph of submodules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acid_engine.level2.conformance import ConformanceResult, ConformanceStatus
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.graph.cycle import detect_cycle
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.graph.rank import compute_rank
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.module.leaf import LeafModule


@dataclass(frozen=True, slots=True)
class CompositeResult:
    """Graph run fact: data, observations, verdict. No conformance — not PASS."""

    data: Any
    observations: tuple[ExecutionObservation, ...] = ()
    conformance: ConformanceResult | None = None

    @property
    def observation(self) -> ExecutionObservation | None:
        return self.observations[-1] if self.observations else None

    @property
    def ok(self) -> bool:
        return bool(self.conformance and self.conformance.ok)

    @property
    def status(self) -> ConformanceStatus | None:
        return None if self.conformance is None else self.conformance.status


@dataclass(frozen=True, slots=True)
class CompositeModule:
    """A module implemented as a graph of modules (Leaf or Composite)."""
    module_id: str
    graph: DependencyGraph
    modules: dict[str, Any]
    contract_id: ContractId
    version: Version
    input_node: str
    output_node: str

    @property
    def content_hash(self) -> str:
        return content_hash_of(self.to_canonical_dict())

    def to_canonical_dict(self) -> dict[str, Any]:
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
        plan: PlanLock | None = None,
        iface: InterfaceContract | None = None,
        toolchain: Any | None = None,
    ) -> CompositeResult:
        import asyncio

        from acid_engine.judge import SELF_LOCK_SKIP
        from acid_engine.level2.conformance import check_conformance
        from acid_engine.level3.script.async_module import AsyncScriptModule
        from acid_engine.level3.script.async_runtime import run_async_script
        from acid_engine.level3.script.runner import (
            bind_script_to_plan,
            execute_plan,
        )

        if detect_cycle(self.graph) is not None:
            raise RuntimeError("Cycle detected in composite module graph")

        if plan is None and iface is None:
            return CompositeResult(
                data=None,
                observations=(),
                conformance=ConformanceResult.skipped(SELF_LOCK_SKIP),
            )
        if (plan is None) != (iface is None):
            return CompositeResult(
                data=None,
                observations=(),
                conformance=ConformanceResult.skipped(
                    "plan and iface must be provided together"
                ),
            )
        assert plan is not None and iface is not None

        ranks = compute_rank(self.graph)
        sorted_nodes = sorted(self.graph.nodes.keys(), key=lambda n: ranks[n])

        node_outputs: dict[str, Any] = {}
        observations: list[ExecutionObservation] = []
        last_conf: ConformanceResult | None = None
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
                leaf_iface, leaf_plan = iface, plan
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
                    step = execute_plan(
                        leaf_iface,
                        leaf_plan,
                        mod.script,
                        input_val,
                        toolchain=toolchain,
                    )
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
                nested = mod.execute(
                    input_val, plan=plan, iface=iface, toolchain=toolchain
                )
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
