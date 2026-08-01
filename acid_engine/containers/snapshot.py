"""Immutable ContainerSnapshot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from acid_engine.contracts.identity import ContractId
from acid_engine.containers.port import PortRef
from acid_engine.contracts.serialization import content_hash_of


@dataclass(frozen=True, slots=True)
class ContainerSnapshot:
    """
    Immutable snapshot of data at a port.
    NOT runtime mutable state.
    """
    port_ref: PortRef
    contract_id: ContractId
    contract_hash: str
    data: Any
    content_hash: str
    cardinality: int = 1
    provenance: str = ""

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