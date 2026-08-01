"""Canonical serialization for deterministic content hashing."""
from __future__ import annotations

import json
from typing import Any


def _normalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _normalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, (list, tuple)):
        return [_normalize(x) for x in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if obj == 0.0:
            return 0.0
        return float(obj)
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if hasattr(obj, "to_canonical_dict"):
        return _normalize(obj.to_canonical_dict())
    if hasattr(obj, "__dict__"):
        return _normalize(
            {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        )
    raise TypeError(f"Cannot canonicalize type {type(obj)!r}")


def canonical_serialize(obj: Any) -> str:
    normalized = _normalize(obj)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def content_hash_of(obj: Any) -> str:
    from acid_engine.contracts.identity import ContentHash
    return ContentHash.from_canonical(canonical_serialize(obj)).value