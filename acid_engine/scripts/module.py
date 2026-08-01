"""ScriptModule — minimal executable unit."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.scripts.specification import Specification
from acid_engine.contracts.serialization import content_hash_of


@dataclass(frozen=True, slots=True)
class ScriptModule:
    """
    Human view: CONSTRAINTS / INPUT / OUTPUT / IMPLEMENTATION
    Core view:  Specification + InputContract + OutputContract + Implementation
    """
    contract_id: ContractId
    version: Version
    specification: Specification
    input_type: str          # simplified type tag for MVP, e.g. "int"
    output_type: str
    implementation: Callable[[Any], Any]
    name: str = ""

    @property
    def content_hash(self) -> str:
        decl = {
            "contract_id": str(self.contract_id),
            "version": str(self.version),
            "specification": self.specification.to_canonical_dict(),
            "input_type": self.input_type,
            "output_type": self.output_type,
            "name": self.name,
        }
        return content_hash_of(decl)

    def to_canonical_dict(self) -> dict:
        return {
            "contract_id": str(self.contract_id),
            "version": str(self.version),
            "specification": self.specification.to_canonical_dict(),
            "input_type": self.input_type,
            "output_type": self.output_type,
            "name": self.name,
            "content_hash": self.content_hash,
        }