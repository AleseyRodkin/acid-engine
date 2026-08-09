"""Базовый класс контракта — единая грамматика для всех сущностей."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Tuple, Optional
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.attributes import Attribute
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level2.specification import Specification


@dataclass(frozen=True, slots=True)
class Contract:
    """
    Универсальный контракт, объединяющий:
    - entity: идентификатор сущности
    - characteristics: атрибуты (оси Origin/Mutability/ValueKind)
    - rules: спецификация (параметры, политики, требования)
    - actions: допустимые операции
    """
    entity: ContractId
    characteristics: Tuple[Attribute, ...] = field(default_factory=tuple)
    rules: Specification = field(default_factory=Specification)
    actions: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def content_hash(self) -> str:
        return content_hash_of(self.to_canonical_dict())

    def to_canonical_dict(self) -> dict:
        return {
            "entity": str(self.entity),
            "characteristics": [a.to_canonical_dict() for a in self.characteristics],
            "rules": self.rules.to_canonical_dict(),
            "actions": list(self.actions),
        }