"""Receipt: Observation + verdict. No proven_pure, no callable, no secrets."""
from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from acid_engine.level2.blank import observation_blank
from acid_engine.level2.serialization import canonical_serialize, content_hash_of
from acid_engine.level3.pipeline import PipelineResult
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.resolve import materialize_script

SCHEMA = "acid.receipt.v1"
_FORBIDDEN = ("proven_pure",)


def _json_safe_output(data: Any) -> Any:
    if callable(data):
        raise TypeError("receipt cannot contain callable")
    canonical_serialize(data)
    return data


def build_receipt(
    script: ScriptModule,
    input_data: Any,
    result: PipelineResult,
    *,
    plan: Any | None = None,
    toolchain: Mapping[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    script = materialize_script(script)
    conf = result.conformance
    status = conf.status.value if hasattr(conf.status, "value") else str(conf.status)
    level = conf.level.value if hasattr(conf.level, "value") else str(conf.level)
    prop = None
    if conf.failure is not None:
        prop = conf.failure.property_name
    obs = None
    if result.observation is not None:
        obs = observation_blank(result.observation)
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: UP017
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "timestamp": ts,
        "script_name": script.name or script.contract_id.name,
        "contract_id": str(script.contract_id),
        "body_hash": script.content_hash,
        "plan_hash": plan.content_hash if plan is not None else None,
        "input_hash": content_hash_of(input_data),
        "output": _json_safe_output(result.data),
        "observation": obs,
        "verdict": {
            "status": status,
            "level": level,
            "message": conf.message,
            "property": prop,
        },
    }
    if toolchain is not None:
        nested = toolchain.get("toolchain") if isinstance(toolchain.get("toolchain"), Mapping) else toolchain
        if isinstance(nested, Mapping):
            receipt["toolchain"] = {
                key: nested[key]
                for key in (
                    "python_version",
                    "canon_kind",
                    "canon",
                    "worker_hash",
                    "runtime_hashes",
                )
                if key in nested
            }
    dumped = canonical_serialize(receipt)
    for banned in _FORBIDDEN:
        if banned in dumped:
            raise ValueError(f"receipt must not contain {banned}")
    return receipt


def write_receipt(path: str | Path, receipt: dict[str, Any]) -> None:
    target = Path(path)
    text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    if "proven_pure" in text:
        raise ValueError("receipt must not contain proven_pure")
    target.write_text(text, encoding="utf-8")
