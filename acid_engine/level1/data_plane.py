"""Абстракция хранилища данных (уровень 1)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

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
    def __init__(self):
        self._store: dict[str, bytes] = {}

    def store(self, key: str, data: bytes) -> None:
        self._store[key] = data

    def load(self, key: str) -> bytes:
        return self._store[key]

    def exists(self, key: str) -> bool:
        return key in self._store