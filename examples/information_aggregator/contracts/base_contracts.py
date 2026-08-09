"""Базовые контракты Information Aggregator Engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Tuple, Optional
from acid_engine.level2.base import Contract
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.attributes import Attribute
from acid_engine.level2.specification import Specification, Policy


@dataclass(frozen=True, slots=True)
class SourceContract(Contract):
    """Контракт источника данных (RSS, API, Telegram, ...)."""
    contract_id: ContractId
    version: Version = Version(1, 0, 0)
    source_type: str = "generic"      # "rss", "api", "telegram", "pdf", ...
    endpoint: str = ""                 # URL или идентификатор источника
    specification: Specification = field(default_factory=Specification)

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_actions(self) -> Tuple[str, ...]:
        return ("fetch", "validate")


@dataclass(frozen=True, slots=True)
class ArticleContract(Contract):
    """Контракт документа (статья, пост, сообщение)."""
    contract_id: ContractId
    version: Version = Version(1, 0, 0)
    fields: Tuple[str, ...] = ("title", "body", "source", "url", "published_at")
    specification: Specification = field(default_factory=Specification)

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_actions(self) -> Tuple[str, ...]:
        return ("store", "normalize", "validate")


@dataclass(frozen=True, slots=True)
class NormalizationContract(Contract):
    """Контракт нормализации (очистка, приведение к единому виду)."""
    contract_id: ContractId
    version: Version = Version(1, 0, 0)
    input_format: str = "any"          # "html", "pdf", "telegram", ...
    output_format: str = "plain_text"  # "plain_text", "json", ...
    specification: Specification = field(default_factory=Specification)

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_actions(self) -> Tuple[str, ...]:
        return ("normalize", "validate")


@dataclass(frozen=True, slots=True)
class StorageContract(Contract):
    """Контракт хранилища (сохранение и поиск)."""
    contract_id: ContractId
    version: Version = Version(1, 0, 0)
    storage_type: str = "atomic"       # "atomic", "file", "database", ...
    specification: Specification = field(default_factory=Specification)

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_actions(self) -> Tuple[str, ...]:
        return ("store", "load", "search", "deduplicate")


@dataclass(frozen=True, slots=True)
class ObservationContract(Contract):
    """Контракт наблюдения (сбор метрик, логирование)."""
    contract_id: ContractId
    version: Version = Version(1, 0, 0)
    metrics: Tuple[str, ...] = ("latency", "success_rate", "cardinality")
    specification: Specification = field(default_factory=Specification)

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_actions(self) -> Tuple[str, ...]:
        return ("observe", "log", "alert")


@dataclass(frozen=True, slots=True)
class AnalysisContract(Contract):
    """Контракт анализа (вызов LLM, построение связей)."""
    contract_id: ContractId
    version: Version = Version(1, 0, 0)
    analysis_type: str = "generic"     # "llm", "entity_extraction", "event_detection", ...
    specification: Specification = field(default_factory=Specification)

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_actions(self) -> Tuple[str, ...]:
        return ("analyze", "report")