"""Типы данных контейнера: scalar, list, record (с вложенностью и default)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RecordField:
    name: str
    type_tag: str  # "int", "float", "str", "bool", "list", "record"
    optional: bool = False
    default: Any = None  # значение по умолчанию, если поле отсутствует
    schema: RecordSchema | None = None  # используется, если type_tag == "record"


@dataclass(frozen=True, slots=True)
class RecordSchema:
    """Описание структуры record с возможной вложенностью."""
    fields: tuple[RecordField, ...] = field(default_factory=tuple)

    def validate(self, data: Any, apply_defaults: bool = True) -> tuple[bool, dict[str, Any] | None]:
        """
        Валидирует данные и, если apply_defaults=True, возвращает 
        заполненный словарь с учётом default-значений.
        Возвращает (valid, filled_data).
        """
        if not isinstance(data, dict):
            return False, None

        filled = dict(data) if apply_defaults else data
        for f in self.fields:
            if f.name not in filled:
                if not f.optional and f.default is None:
                    return False, None
                if apply_defaults and f.default is not None:
                    filled[f.name] = f.default
                continue

            value = filled[f.name]
            # Проверка типа
            if not self._check_type(value, f):
                return False, None

            # Рекурсивная проверка вложенной record
            if f.type_tag == "record" and f.schema is not None:
                ok, _ = f.schema.validate(value, apply_defaults)
                if not ok:
                    return False, None

        return True, filled if apply_defaults else data

    def _check_type(self, value: Any, field: RecordField) -> bool:
        t = field.type_tag
        if t == "int" and not isinstance(value, int):
            return False
        if t == "float" and not isinstance(value, (int, float)):
            return False
        if t == "str" and not isinstance(value, str):
            return False
        if t == "bool" and not isinstance(value, bool):
            return False
        if t == "list" and not isinstance(value, list):
            return False
        if t == "record" and not isinstance(value, dict):
            return False
        return True

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "fields": [
                {
                    "name": f.name,
                    "type_tag": f.type_tag,
                    "optional": f.optional,
                    "default": f.default,
                    "schema": f.schema.to_canonical_dict() if f.schema else None,
                }
                for f in self.fields
            ]
        }