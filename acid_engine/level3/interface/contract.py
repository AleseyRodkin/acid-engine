"""Interface Contract — MAX level."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional, Callable
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level2.base import Contract
from acid_engine.level2.attributes import Attribute


@dataclass(frozen=True, slots=True)
class InterfaceContract(Contract):
    contract_id: ContractId
    version: Version
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    constraints: Dict[str, Any]
    capabilities: List[str] = field(default_factory=list)
    provenance: str = ""
    module_hashes: Dict[str, str] = field(default_factory=dict)
    invariants: Optional[Tuple[Callable[[Any], bool], ...]] = None

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_actions(self) -> Tuple[str, ...]:
        return ("validate", "execute")

    @property
    def content_hash(self) -> str:
        return content_hash_of(self.to_canonical_dict())

    def to_canonical_dict(self) -> dict:
        return {
            "contract_id": str(self.contract_id),
            "version": str(self.version),
            "inputs": self.inputs,
            "outputs": self.outputs,
            "constraints": self.constraints,
            "capabilities": self.capabilities,
            "provenance": self.provenance,
            "module_hashes": self.module_hashes,
        }