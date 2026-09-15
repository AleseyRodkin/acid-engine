"""Data store abstraction (level 1). A write is an observed effect."""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from pathlib import Path

from acid_engine.level1.effects import record_effect


class DataPlane(ABC):
    @abstractmethod
    def store(self, key: str, data: bytes) -> None:
        ...

    @abstractmethod
    def load(self, key: str) -> bytes:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...


class InMemoryDataPlane(DataPlane):
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def store(self, key: str, data: bytes) -> None:
        self._store[key] = data
        record_effect(f"dataplane.store:{key}")

    def load(self, key: str) -> bytes:
        return self._store[key]

    def exists(self, key: str) -> bool:
        return key in self._store


class FileSystemDataPlane(DataPlane):
    """File store: blob by sha256(key), index key→digest."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / "index.json"
        self._index: dict[str, str] = {}
        if self._index_path.exists():
            self._index = json.loads(self._index_path.read_text(encoding="utf-8"))

    def _blob_path(self, digest: str) -> Path:
        return self.root / digest

    def _save_index(self) -> None:
        self._index_path.write_text(
            json.dumps(self._index, sort_keys=True), encoding="utf-8"
        )

    def store(self, key: str, data: bytes) -> None:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        self._blob_path(digest).write_bytes(data)
        self._index[key] = digest
        self._save_index()
        record_effect(f"dataplane.store:{key}")

    def load(self, key: str) -> bytes:
        digest = self._index.get(key)
        if digest is None:
            raise KeyError(key)
        path = self._blob_path(digest)
        if not path.exists():
            raise KeyError(key)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        digest = self._index.get(key)
        if digest is None:
            return False
        return self._blob_path(digest).exists()
