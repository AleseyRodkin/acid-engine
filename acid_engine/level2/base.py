"""Базовый класс контракта — единая грамматика для всех сущностей."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acid_engine.level2.attributes import Attribute
from acid_engine.level2.identity import ContractId


@dataclass(frozen=True, slots=True)
class Contract:
    """
    Универсальный интерфейс контракта. Наследники реализуют:
    - get_entity() -> ContractId
    - get_characteristics() -> Tuple[Attribute, ...]
    - get_actions() -> Tuple[str, ...]
    """

    def get_entity(self) -> ContractId:
        raise NotImplementedError("Subclasses must implement get_entity()")

    def get_characteristics(self) -> tuple[Attribute, ...]:
        return ()

    def get_actions(self) -> tuple[str, ...]:
        return ()

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "entity": str(self.get_entity()),
            "characteristics": [a.to_canonical_dict() for a in self.get_characteristics()],
            "actions": list(self.get_actions()),
        }