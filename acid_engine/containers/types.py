"""Типы данных контейнера: scalar, list, record."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True, slots=True)
class RecordField:
    name: str
    type_tag: str  # "int", "float", "str", "bool"
    optional: bool = False


@dataclass(frozen=True, slots=True)
class RecordSchema:
    """Описание структуры record (аналог таблицы)."""
    fields: tuple[RecordField, ...] = field(default_factory=tuple)

    def validate(self, data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        field_names = {f.name for f in self.fields}
        required = {f.name for f in self.fields if not f.optional}
        if not required.issubset(data.keys()):
            return False
        for f in self.fields:
            if f.name not in data:
                continue
            value = data[f.name]
            if f.type_tag == "int" and not isinstance(value, int):
                return False
            if f.type_tag == "float" and not isinstance(value, (int, float)):
                return False
            if f.type_tag == "str" and not isinstance(value, str):
                return False
            if f.type_tag == "bool" and not isinstance(value, bool):
                return False
        return True

    def to_canonical_dict(self) -> dict:
        return {
            "fields": [
                {"name": f.name, "type_tag": f.type_tag, "optional": f.optional}
                for f in self.fields
            ]
        }