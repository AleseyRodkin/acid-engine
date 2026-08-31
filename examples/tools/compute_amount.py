"""Money in minor units. bool is not int."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def compute_amount(data: dict) -> dict:
    if type(data) is not dict:
        raise TypeError("expected dict")
    cents = data.get("cents")
    qty = data.get("qty")
    if type(cents) is not int:
        raise TypeError("cents must be int")
    if type(qty) is not int:
        raise TypeError("qty must be int")
    if cents < 0 or qty < 0:
        raise ValueError("cents and qty must be >= 0")
    return {"cents": cents * qty}


def build_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("tools", "compute_amount"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200.0)),
        input_type="dict",
        output_type="dict",
        implementation=compute_amount,
        name="compute_amount",
    )


script = build_script()
