"""ScriptModule — минимальная исполняемая единица."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from acid_engine.level2.attributes import Attribute
from acid_engine.level2.base import Contract
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.implementation_canon import canonical_implementation
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level2.specification import Specification
from acid_engine.level3.script.artifact import ArtifactRef


@dataclass(frozen=True, slots=True)
class ScriptModule(Contract):
    contract_id: ContractId
    version: Version
    specification: Specification
    input_type: str
    output_type: str
    implementation: Callable[[Any], Any] | None = None
    name: str = ""
    artifact: ArtifactRef | None = None

    def get_entity(self) -> ContractId:
        return self.contract_id

    def get_characteristics(self) -> tuple[Attribute, ...]:
        return ()

    def get_actions(self) -> tuple[str, ...]:
        return ("execute",)

    def _identity_dict(self) -> dict[str, Any]:
        if self.implementation is not None:
            impl = canonical_implementation(self.implementation)
        elif self.artifact is not None:
            impl = self.artifact.to_canonical_dict()
        else:
            impl = {"kind": "missing"}
        return {
            "contract_id": str(self.contract_id),
            "version": str(self.version),
            "specification": self.specification.to_canonical_dict(),
            "input_type": self.input_type,
            "output_type": self.output_type,
            "name": self.name,
            "implementation": impl,
        }

    @property
    def content_hash(self) -> str:
        return content_hash_of(self._identity_dict())

    def to_canonical_dict(self) -> dict[str, Any]:
        body = self._identity_dict()
        body["content_hash"] = self.content_hash
        return body
