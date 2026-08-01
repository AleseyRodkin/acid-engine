"""Contract attribute model with independent axes."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Origin(str, Enum):
    SYSTEM = "system"
    USER = "user"


class Mutability(str, Enum):
    EDITABLE = "editable"
    LOCKED = "locked"


class ValueKind(str, Enum):
    FACTUAL = "factual"
    COMPUTED = "computed"
    REFERENCE = "reference"


@dataclass(frozen=True, slots=True)
class Attribute:
    """Single attribute with three independent axes."""
    name: str
    value: Any
    origin: Origin = Origin.USER
    mutability: Mutability = Mutability.EDITABLE
    value_kind: ValueKind = ValueKind.FACTUAL

    def to_canonical_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "origin": self.origin.value,
            "mutability": self.mutability.value,
            "value_kind": self.value_kind.value,
        }


@dataclass(frozen=True, slots=True)
class AttributeSet:
    attributes: tuple[Attribute, ...] = field(default_factory=tuple)

    def get(self, name: str) -> Optional[Attribute]:
        for a in self.attributes:
            if a.name == name:
                return a
        return None

    def to_canonical_dict(self) -> dict:
        return {
            "attributes": [a.to_canonical_dict() for a in self.attributes]
        }