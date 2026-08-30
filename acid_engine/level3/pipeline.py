"""Pipeline — замкнутый контур: контракт → execute_plan → conformance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from acid_engine.level2.base import Contract
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level2.conformance import ConformanceResult


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

    @property
    def failure(self):
        return self.conformance.failure


class Pipeline:
    """Замкнутый контур. ScriptModule исполняется только через execute_plan / plan.lock."""

    def __init__(
        self,
        contract: Contract,
        registry: Optional[Any] = None,
        plan: Optional[PlanLock] = None,
        iface: Optional[InterfaceContract] = None,
    ):
        self.contract = contract
        self.registry = registry
        self.plan = plan
        self.iface = iface

    def execute(self, input_data: Any) -> PipelineResult:
        from acid_engine.level3.script.runner import execute_plan, lock_for_script

        script = None
        if isinstance(self.contract, ScriptModule):
            script = self.contract
        elif isinstance(self.contract, LeafModule):
            script = self.contract.script

        if script is not None:
            iface, plan = self.iface, self.plan
            if iface is None or plan is None:
                iface, plan = lock_for_script(script)
            return execute_plan(iface, plan, script, input_data)

        if isinstance(self.contract, InterfaceContract):
            return PipelineResult(
                conformance=ConformanceResult.skipped(
                    "InterfaceContract was not executed"
                ),
                data=None,
                observation=None,
            )

        raise TypeError(f"Unsupported contract type: {type(self.contract)}")
