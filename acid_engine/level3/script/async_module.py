"""AsyncScriptModule — асинхронный вариант ScriptModule."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Optional
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level2.implementation_canon import canonical_implementation
from acid_engine.level3.script.artifact import ArtifactRef


@dataclass(frozen=True, slots=True)
class AsyncScriptModule:
    """
    Аналог ScriptModule, но implementation — асинхронная функция (async def).
    """
    contract_id: ContractId
    version: Version
    specification: Specification
    input_type: str
    output_type: str
    implementation: Optional[Callable[[Any], Coroutine[Any, Any, Any]]] = None
    name: str = ""
    artifact: Optional[ArtifactRef] = None

    def _identity_dict(self) -> dict:
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

    def to_canonical_dict(self) -> dict:
        body = self._identity_dict()
        body["content_hash"] = self.content_hash
        return body
