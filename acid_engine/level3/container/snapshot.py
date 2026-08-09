"""Immutable ContainerSnapshot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple
from acid_engine.level2.identity import ContractId
from acid_engine.level3.container.port import PortRef
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level2.base import Contract
from acid_engine.level2.attributes import Attribute


@dataclass(frozen=True, slots=True)
class ContainerSnapshot(Contract):
    port_ref: PortRef
    contract_id: ContractId
    contract_hash: str
    data: Any
    content_hash: str
    cardinality: int = 1
    provenance: str = ""

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_actions(self) -> Tuple[str, ...]:
        return ("store", "load", "validate")

    @staticmethod
    def create(
        port_ref: PortRef,
        contract_id: ContractId,
        contract_hash: str,
        data: Any,
        cardinality: int = 1,
        provenance: str = "",
    ) -> ContainerSnapshot:
        ch = content_hash_of(data)
        return ContainerSnapshot(
            port_ref=port_ref,
            contract_id=contract_id,
            contract_hash=contract_hash,
            data=data,
            content_hash=ch,
            cardinality=cardinality,
            provenance=provenance,
        )

    def to_canonical_dict(self) -> dict:
        return {
            "port_ref": str(self.port_ref),
            "contract_id": str(self.contract_id),
            "contract_hash": self.contract_hash,
            "content_hash": self.content_hash,
            "cardinality": self.cardinality,
            "provenance": self.provenance,
        }