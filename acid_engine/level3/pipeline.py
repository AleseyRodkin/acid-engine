"""Pipeline — замкнутый контур выполнения контракта (уровень 3)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from acid_engine.level2.base import Contract
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.script.python_runtime import run_script
from acid_engine.level2.conformance import check_conformance, ConformanceResult
from acid_engine.level2.specification import Policy


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Факт прогона: данные, observation (если было исполнение), conformance."""

    conformance: ConformanceResult
    data: Any = None
    observation: Optional[ExecutionObservation] = None

    @property
    def ok(self) -> bool:
        return self.conformance.ok

    @property
    def status(self):
        return self.conformance.status

    @property
    def message(self) -> str:
        return self.conformance.message


class Pipeline:
    """Замкнутый контур: контракт → исполнение (если есть) → conformance."""

    def __init__(self, contract: Contract, registry: Optional[Any] = None):
        self.contract = contract
        self.registry = registry

    def execute(self, input_data: Any) -> PipelineResult:
        if isinstance(self.contract, ScriptModule):
            in_port = PortRef(
                module=self.contract.contract_id.name,
                direction="input",
                name="value",
            )
            input_snap = ContainerSnapshot.create(
                port_ref=in_port,
                contract_id=self.contract.contract_id,
                contract_hash=self.contract.content_hash,
                data=input_data,
            )
            output_snap, obs, _delta, _state = run_script(self.contract, input_snap)
            policy = (
                self.contract.specification.policy
                if hasattr(self.contract.specification, "policy")
                else Policy()
            )
            conf = check_conformance(
                required_output_type=self.contract.output_type,
                provided_data=output_snap.data,
                obs=obs,
                policy=policy,
                node_id=self.contract.name,
                contract_id=str(self.contract.contract_id),
            )
            return PipelineResult(
                conformance=conf,
                data=output_snap.data,
                observation=obs,
            )

        if isinstance(self.contract, InterfaceContract):
            # Нет исполнения — нет Observed. Нельзя PASS.
            return PipelineResult(
                conformance=ConformanceResult.skipped(
                    "InterfaceContract was not executed"
                ),
                data=None,
                observation=None,
            )

        raise TypeError(f"Unsupported contract type: {type(self.contract)}")
