"""Isolated atom store (AtomicStorage)."""
from __future__ import annotations

import json

from acid_engine.level1.data_plane import DataPlane, InMemoryDataPlane
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level4.registry import ContractRegistry


class AtomicStorage:
    """
    Persistent ScriptModule store with versioning and lookup.
    Uses DataPlane for data (in-memory by default).
    """
    def __init__(self, data_plane: DataPlane | None = None):
        self.registry = ContractRegistry()
        self.data_plane = data_plane or InMemoryDataPlane()
        self._index: dict[str, list[str]] = {}  # contract_id -> list of hashes

    def store(self, module: ScriptModule) -> None:
        """Save the module in the store and the registry."""
        key = str(module.contract_id)
        # Store the module as JSON in DataPlane
        serialized = json.dumps(module.to_canonical_dict(), ensure_ascii=False)
        content_hash = module.content_hash
        self.data_plane.store(f"{key}:{content_hash}", serialized.encode("utf-8"))
        # Update the version index
        if key not in self._index:
            self._index[key] = []
        self._index[key].append(content_hash)
        # Register in the registry
        self.registry.register(module)

    def load(self, contract_id: ContractId, version_hash: str | None = None) -> ScriptModule:
        """Load a module by id and (optionally) version."""
        key = str(contract_id)
        if version_hash is None:
            # Latest version
            if key not in self._index or not self._index[key]:
                raise KeyError(f"No versions for {key}")
            version_hash = self._index[key][-1]
        data = self.data_plane.load(f"{key}:{version_hash}")
        # Restore the object from a dict (simplified)
        d = json.loads(data.decode("utf-8"))
        # Build ScriptModule (implementation will be a stub)
        return ScriptModule(
            contract_id=contract_id,
            version=Version(*(d.get("version", "0.0.0").split("."))),
            specification=None,  # not restored
            input_type=d.get("input_type", "any"),
            output_type=d.get("output_type", "any"),
            implementation=lambda x: x,
            name=d.get("name", "")
        )

    def list_versions(self, contract_id: ContractId) -> list[str]:
        """Return hashes of every module version."""
        return self._index.get(str(contract_id), [])

    def search_by_hash(self, content_hash: str) -> ContractId | None:
        """Find a module by content hash."""
        for cid, hashes in self._index.items():
            if content_hash in hashes:
                ns, name = cid.split("/", 1)
                return ContractId(ns, name)
        return None