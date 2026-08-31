"""SKU/id without surprise: strip, upper, no inner spaces."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def normalize_id(data: dict) -> dict:
    if type(data) is not dict:
        raise TypeError("expected dict")
    raw = data.get("id")
    if type(raw) is not str:
        raise TypeError("id must be str")
    ident = "".join(raw.split()).upper()
    if not ident:
        raise ValueError("id is empty")
    return {"id": ident}


def build_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("tools", "normalize_id"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200.0)),
        input_type="dict",
        output_type="dict",
        implementation=normalize_id,
        name="normalize_id",
    )


script = build_script()
