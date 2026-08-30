"""ArtifactRef — ссылка на тело рядом с callable. В фазе 2a не входит в хеш."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from acid_engine.level2.implementation_canon import canonical_implementation
from acid_engine.level2.serialization import content_hash_of

CANON_KINDS = frozenset({"ast", "bytecode", "opaque", "partial", "cycle"})


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    language: str
    file: str
    entry: str
    canon: str
    body_hash: str

    def __post_init__(self) -> None:
        if self.canon not in CANON_KINDS:
            raise ValueError(
                f"canon must be one of {sorted(CANON_KINDS)}, got {self.canon!r}"
            )

    def to_canonical_dict(self) -> dict[str, str]:
        return {
            "language": self.language,
            "file": self.file,
            "entry": self.entry,
            "canon": self.canon,
            "body_hash": self.body_hash,
        }


def artifact_ref_from_callable(
    fn: Callable[..., Any],
    *,
    language: str = "python",
    file: str = "",
    entry: str = "",
) -> ArtifactRef:
    """Собрать ссылку из живой функции. canon = kind из canonical_implementation."""
    impl = canonical_implementation(fn)
    kind = impl.get("kind", "opaque")
    if kind not in CANON_KINDS:
        kind = "opaque"
    path = file
    if not path:
        code = getattr(fn, "__code__", None)
        path = getattr(code, "co_filename", "") or ""
    name = entry or getattr(fn, "__qualname__", "") or getattr(fn, "__name__", "") or ""
    return ArtifactRef(
        language=language,
        file=path,
        entry=name,
        canon=kind,
        body_hash=content_hash_of(impl),
    )
