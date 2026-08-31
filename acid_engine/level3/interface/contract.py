"""Interface Contract — MAX level."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from acid_engine.level2.base import Contract
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.serialization import content_hash_of


@dataclass(frozen=True, slots=True)
class InterfaceContract(Contract):
    contract_id: ContractId
    version: Version
    inputs: dict[str, str]
    outputs: dict[str, str]
    constraints: dict[str, Any]
    capabilities: list[str] = field(default_factory=list)
    provenance: str = ""
    module_hashes: dict[str, str] = field(default_factory=dict)
    invariants: tuple[Callable[[Any], bool], ...] | None = None

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_actions(self) -> tuple[str, ...]:
        return ("validate", "execute")

    @property
    def content_hash(self) -> str:
        return content_hash_of(self.to_canonical_dict())

    def to_canonical_dict(self) -> dict[str, Any]:
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