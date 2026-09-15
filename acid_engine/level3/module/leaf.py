"""LeafModule — holds one ScriptModule."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acid_engine.level2.identity import ContractId
from acid_engine.level3.script.module import ScriptModule


@dataclass(frozen=True, slots=True)
class LeafModule:
    """A module that contains exactly one script."""
    module_id: str
    script: ScriptModule

    @property
    def contract_id(self) -> ContractId:
        return self.script.contract_id

    @property
    def content_hash(self) -> str:
        return self.script.content_hash

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "kind": "leaf",
            "module_id": self.module_id,
            "script": self.script.to_canonical_dict(),
        }