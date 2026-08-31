"""Pipeline — замкнутый контур: контракт → execute_plan → conformance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acid_engine.level2.base import Contract
from acid_engine.level2.conformance import ConformanceResult, ConformanceStatus
from acid_engine.level2.failure import FailureReason
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.script.module import ScriptModule


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Факт прогона: данные, observation (если было исполнение), conformance."""

    conformance: ConformanceResult
    data: Any = None
    observation: ExecutionObservation | None = None

    @property
    def ok(self) -> bool:
        return self.conformance.ok

    @property
    def status(self) -> ConformanceStatus:
        return self.conformance.status

    @property
    def message(self) -> str:
        return self.conformance.message

    @property
    def failure(self) -> FailureReason | None:
        return self.conformance.failure


class Pipeline:
    """Замкнутый контур. ScriptModule исполняется только через execute_plan / plan.lock."""

    def __init__(
        self,
        contract: Contract,
        registry: Any | None = None,
        plan: PlanLock | None = None,
        iface: InterfaceContract | None = None,
    ):
        self.contract = contract
        self.registry = registry
        self.plan = plan
        self.iface = iface

    def execute(self, input_data: Any) -> PipelineResult:
        from acid_engine.judge import judge_script

        script = None
        if isinstance(self.contract, ScriptModule):
            script = self.contract
        elif isinstance(self.contract, LeafModule):
            script = self.contract.script

        if script is not None:
            return judge_script(
                script, input_data, plan=self.plan, iface=self.iface
            )

        if isinstance(self.contract, InterfaceContract):
            return PipelineResult(
                conformance=ConformanceResult.skipped(
                    "InterfaceContract was not executed"
                ),
                data=None,
                observation=None,
            )

        raise TypeError(f"Unsupported contract type: {type(self.contract)}")
