"""Contract identity primitives."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from enum import Enum


class HashAlgorithm(str, Enum):
    SHA256 = "sha256"
    BLAKE3 = "blake3"  # зарезервировано, пока используем SHA-256


@dataclass(frozen=True, slots=True)
class Version:
    major: int
    minor: int = 0
    patch: int = 0
    label: str = ""

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.label}" if self.label else base

    def __lt__(self, other: Version) -> bool:
        return (self.major, self.minor, self.patch) < (
            other.major, other.minor, other.patch
        )


@dataclass(frozen=True, slots=True)
class ContractId:
    namespace: str
    name: str

    def __str__(self) -> str:
        return f"{self.namespace}/{self.name}"

    @staticmethod
    def parse(s: str) -> ContractId:
        if "/" not in s:
            raise ValueError(f"Invalid ContractId: {s!r}")
        ns, name = s.split("/", 1)
        return ContractId(namespace=ns, name=name)


@dataclass(frozen=True, slots=True)
class ContentHash:
    value: str
    algorithm: HashAlgorithm = HashAlgorithm.SHA256

    def __str__(self) -> str:
        return f"{self.algorithm.value}:{self.value}"

    @staticmethod
    def from_bytes(data: bytes, algo: HashAlgorithm = HashAlgorithm.SHA256) -> ContentHash:
        h = hashlib.sha256(data).hexdigest()
        return ContentHash(value=h, algorithm=algo)

    @staticmethod
    def from_canonical(canonical: str) -> ContentHash:
        return ContentHash.from_bytes(canonical.encode("utf-8"))