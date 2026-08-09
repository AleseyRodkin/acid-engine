"""ScriptModule — минимальная исполняемая единица."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Tuple
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level2.base import Contract
from acid_engine.level2.attributes import Attribute


@dataclass(frozen=True, slots=True)
class ScriptModule(Contract):
    contract_id: ContractId
    version: Version
    specification: Specification
    input_type: str
    output_type: str
    implementation: Callable[[Any], Any]
    name: str = ""

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_characteristics(self) -> Tuple[Attribute, ...]:
        # Пока возвращаем пустой кортеж, можно расширить позже
        return ()

    def get_actions(self) -> Tuple[str, ...]:
        return ("execute",)

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