"""Адаптер для подключения внешних оркестраторов."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level2.conformance import ConformanceResult


class OrchestratorAdapter(ABC):
    """Интерфейс адаптера для внешнего оркестратора."""

    @abstractmethod
    def submit_plan(self, plan: PlanLock) -> str:
        """Отправить план на исполнение, вернуть external_run_id."""
        ...

    @abstractmethod
    def get_status(self, external_run_id: str) -> str:
        """Получить статус выполнения."""
        ...

    @abstractmethod
    def get_result(self, external_run_id: str) -> Optional[ConformanceResult]:
        """Получить результат выполнения, если готов."""
        ...


class LocalAdapter(OrchestratorAdapter):
    """Заглушка для локального исполнения (без внешнего оркестратора)."""

    def submit_plan(self, plan: PlanLock) -> str:
        return f"local-{plan.plan_id}"

    def get_status(self, external_run_id: str) -> str:
        return "completed"

    def get_result(self, external_run_id: str) -> Optional[ConformanceResult]:
        from acid_engine.level2.conformance import (
            ConformanceResult, ConformanceStatus, ConformanceLevel,
        )
        return ConformanceResult(
            status=ConformanceStatus.PASS,
            level=ConformanceLevel.OPERATIONAL,
            message="Local execution (adapter placeholder)",
        )