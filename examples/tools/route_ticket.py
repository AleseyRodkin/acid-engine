"""Agent does not invent a queue. Unknown queue fails closed."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def route_ticket(data: dict) -> dict:
    if type(data) is not dict:
        raise TypeError("expected dict")
    queue = data.get("queue")
    if type(queue) is not str:
        raise TypeError("queue must be str")
    allowed = ("billing", "support", "ops")
    if queue not in allowed:
        raise ValueError("unknown queue")
    return {"queue": queue}


def build_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("tools", "route_ticket"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200.0)),
        input_type="dict",
        output_type="dict",
        implementation=route_ticket,
        name="route_ticket",
    )


script = build_script()
