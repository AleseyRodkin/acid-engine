"""normalize strings: strip, collapse space, lower."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def clean_text(data: dict) -> dict:
    if type(data) is not dict:
        raise TypeError("expected dict")
    text = data.get("text")
    if type(text) is not str:
        raise TypeError("text must be str")
    parts = text.split()
    return {"text": " ".join(parts).lower()}


def build_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("tools", "clean_text"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200.0)),
        input_type="dict",
        output_type="dict",
        implementation=clean_text,
        name="clean_text",
    )


script = build_script()
