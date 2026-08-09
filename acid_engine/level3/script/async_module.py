"""AsyncScriptModule — асинхронный вариант ScriptModule."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Coroutine
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level2.serialization import content_hash_of


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
    implementation: Callable[[Any], Coroutine[Any, Any, Any]]
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