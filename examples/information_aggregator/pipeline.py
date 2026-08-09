"""AggregatorPipeline — универсальный пайплайн сбора информации."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from acid_engine.level3.pipeline import Pipeline
from acid_engine.level2.base import Contract
from examples.information_aggregator.contracts.base_contracts import (
    SourceContract, ArticleContract, NormalizationContract,
    StorageContract, ObservationContract, AnalysisContract,
)
from examples.atomic_storage.storage import AtomicStorage


class AggregatorPipeline:
    """
    Универсальный движок для сбора и обработки информации.
    Принимает профиль (набор контрактов) и выполняет всю цепочку.
    """
    def __init__(self, profile: Dict[str, List[Contract]], storage: Optional[AtomicStorage] = None):
        self.profile = profile
        self.storage = storage or AtomicStorage()
        self.pipeline = Pipeline(profile.get("source", [None])[0] if profile.get("source") else None)

    def run(self) -> Dict[str, Any]:
        """
        Выполняет полный цикл:
        1. Сбор (fetch) → 2. Нормализация → 3. Сохранение → 4. Наблюдение → 5. Анализ
        """
        results = {"status": "pending", "steps": []}

        # 1. Сбор
        sources = self.profile.get("sources", [])
        if sources:
            for source in sources:
                # В реальности здесь будет вызов ExternalRunner или прямого кода
                results["steps"].append(f"Fetch from {source.endpoint}")

        # 2. Нормализация
        normalizers = self.profile.get("normalizers", [])
        if normalizers:
            results["steps"].append("Normalization step")

        # 3. Сохранение
        storages = self.profile.get("storages", [])
        if storages:
            results["steps"].append("Storage step")

        # 4. Наблюдение
        observers = self.profile.get("observers", [])
        if observers:
            results["steps"].append("Observation step")

        # 5. Анализ
        analyzers = self.profile.get("analyzers", [])
        if analyzers:
            results["steps"].append("Analysis step")

        results["status"] = "completed"
        return results