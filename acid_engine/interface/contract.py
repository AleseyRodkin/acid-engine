"""Interface Contract — MAX level."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.contracts.serialization import content_hash_of


@dataclass(frozen=True, slots=True)
class InterfaceContract:
    contract_id: ContractId
    version: Version
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    constraints: Dict[str, Any]
    capabilities: List[str] = field(default_factory=list)
    provenance: str = ""
    module_hashes: Dict[str, str] = field(default_factory=dict)
    # Рантайм-инварианты (функции), не сериализуются
    invariants: Optional[tuple[Callable[[Any], bool], ...]] = None

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