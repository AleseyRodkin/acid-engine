"""Container data types: scalar, list, record (with nesting and default)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acid_engine.level2.conformance import _KNOWN_OUTPUT_TYPES, _type_matches


@dataclass(frozen=True, slots=True)
class RecordField:
    name: str
    type_tag: str  # "int", "float", "str", "bool", "list", "record"
    optional: bool = False
    default: Any = None  # default when the field is absent
    schema: RecordSchema | None = None  # used when type_tag == "record"


@dataclass(frozen=True, slots=True)
class RecordSchema:
    """Record structure, possibly nested."""
    fields: tuple[RecordField, ...] = field(default_factory=tuple)

    def validate(self, data: Any, apply_defaults: bool = True) -> tuple[bool, dict[str, Any] | None]:
        """
        Validate data and, if apply_defaults=True, return 
        a filled dict applying default values.
        Returns (valid, filled_data).
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
            # Type check
            if not self._check_type(value, f):
                return False, None

            # Recursive check of a nested record
            if f.type_tag == "record" and f.schema is not None:
                ok, _ = f.schema.validate(value, apply_defaults)
                if not ok:
                    return False, None

        return True, filled if apply_defaults else data

    def _check_type(self, value: Any, field: RecordField) -> bool:
        tag = field.type_tag
        if tag not in _KNOWN_OUTPUT_TYPES:
            return False
        return _type_matches(tag, value)

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
