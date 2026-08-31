"""Consistency card from given fields. Not a news product."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def emit_forecast_card(data: dict) -> dict:
    if type(data) is not dict:
        raise TypeError("expected dict")
    title = data.get("title")
    items = data.get("items")
    if type(title) is not str:
        raise TypeError("title must be str")
    if type(items) is not list:
        raise TypeError("items must be list")
    for item in items:
        if type(item) is not str:
            raise TypeError("items must be list of str")
    return {"title": title, "count": len(items)}


def build_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("tools", "emit_forecast_card"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200.0)),
        input_type="dict",
        output_type="dict",
        implementation=emit_forecast_card,
        name="emit_forecast_card",
    )


script = build_script()
