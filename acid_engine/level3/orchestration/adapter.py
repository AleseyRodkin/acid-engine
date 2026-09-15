"""Adapter for attaching external orchestrators."""
from __future__ import annotations

from abc import ABC, abstractmethod

from acid_engine.level2.conformance import ConformanceResult
from acid_engine.level3.bootstrap.plan_lock import PlanLock


class OrchestratorAdapter(ABC):
    """Adapter interface for an external orchestrator."""

    @abstractmethod
    def submit_plan(self, plan: PlanLock) -> str:
        """Submit a plan for execution, return external_run_id."""
        ...

    @abstractmethod
    def get_status(self, external_run_id: str) -> str:
        """Get execution status."""
        ...

    @abstractmethod
    def get_result(self, external_run_id: str) -> ConformanceResult | None:
        """Get the execution result if ready."""
        ...


class LocalAdapter(OrchestratorAdapter):
    """Placeholder. Does not execute the plan and has no right to return PASS."""

    def submit_plan(self, plan: PlanLock) -> str:
        return f"local-{plan.plan_id}"

    def get_status(self, external_run_id: str) -> str:
        return "not_executed"

    def get_result(self, external_run_id: str) -> ConformanceResult | None:
        return ConformanceResult.skipped(
            "LocalAdapter is a placeholder; no execution was observed"
        )
