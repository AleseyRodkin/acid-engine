"""Resolve the body: a live callable or ArtifactRef. Foreign languages are not eval'd."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from acid_engine.level2.conformance import (
    ConformanceLevel,
    ConformanceResult,
    ConformanceStatus,
)
from acid_engine.level2.failure import FailureReason
from acid_engine.level2.implementation_canon import canonical_implementation
from acid_engine.level2.serialization import content_hash_of

MISSING = "missing_implementation"
UNKNOWN_LANGUAGE = "unknown_language"
BROKEN_REF = "broken_ref"
BODY_HASH = "body_hash"
SOURCE_HASH = "source_hash"


def resolve_script(script: Any) -> tuple[Callable[..., Any] | None, str | None]:
    """
    (fn, None) — may be called.
    (None, code) — do not execute. code: missing_implementation | unknown_language:... | broken_ref:... | body_hash:... | source_hash:...
    """
    impl = getattr(script, "implementation", None)
    if callable(impl):
        return impl, None

    artifact = getattr(script, "artifact", None)
    if artifact is None:
        return None, MISSING

    language = (artifact.language or "").strip().lower()
    if language != "python":
        return None, f"{UNKNOWN_LANGUAGE}:{artifact.language}"

    path = Path(artifact.file)
    if not path.is_file():
        return None, f"{BROKEN_REF}:file not found: {artifact.file}"

    entry = artifact.entry or ""
    if not entry:
        return None, f"{BROKEN_REF}:empty entry"

    try:
        fn = _load_python_entry(
            path,
            entry,
            expected_body_hash=artifact.body_hash or "",
            expected_source_hash=artifact.source_hash or "",
        )
    except ValueError as e:
        msg = str(e)
        if "source_hash" in msg:
            return None, f"{SOURCE_HASH}:mismatch"
        if artifact.body_hash and "body_hash" in msg:
            return None, f"{BODY_HASH}:mismatch"
        return None, f"{BROKEN_REF}:{e}"
    except Exception as e:
        return None, f"{BROKEN_REF}:{e}"

    if not callable(fn):
        return None, f"{BROKEN_REF}:entry {entry!r} is not callable"

    if artifact.body_hash:
        actual = content_hash_of(canonical_implementation(fn))
        if actual != artifact.body_hash:
            return None, f"{BODY_HASH}:mismatch"

    return fn, None


def materialize_script(script: Any) -> Any:
    """After resolve, identity is the fn body. If it does not resolve — the script as it was."""
    from dataclasses import replace

    impl = getattr(script, "implementation", None)
    if callable(impl):
        return script
    fn, _err = resolve_script(script)
    if fn is None:
        return script
    return replace(script, implementation=fn)


def _load_python_entry(
    path: Path,
    entry: str,
    *,
    expected_body_hash: str = "",
    expected_source_hash: str = "",
) -> Any:
    """Snapshot bytes, compare hashes, pin, then exec. Mismatch does not import."""
    import hashlib

    from acid_engine.level2.implementation_canon import (
        canonical_implementation_from_source,
    )
    from acid_engine.level2.local_deps import (
        exec_source_module,
        pin_source_bytes,
        read_source_bytes,
    )

    source = Path(path)
    src = read_source_bytes(source)
    if expected_source_hash:
        actual_file = hashlib.sha256(src).hexdigest()
        if actual_file != expected_source_hash:
            raise ValueError("source_hash mismatch")
    if expected_body_hash:
        preview_impl = canonical_implementation_from_source(src, entry)
        preview = content_hash_of(preview_impl) if preview_impl is not None else None
        if preview != expected_body_hash:
            raise ValueError("body_hash does not match resolved implementation")
    pin_source_bytes(source, src)
    src = read_source_bytes(source)
    mod_name = f"acid_artifact_{source.stem}_{abs(hash(str(source.resolve())))}"
    module = exec_source_module(source, src, mod_name)
    obj: Any = module
    for part in entry.split("."):
        obj = getattr(obj, part)
    return obj


def unresolved_conformance(script: Any, code: str) -> ConformanceResult:
    node = getattr(script, "name", "") or ""
    cid = str(getattr(script, "contract_id", ""))
    if code == MISSING:
        return ConformanceResult.skipped(
            "no implementation and no artifact"
        )
    if code.startswith(UNKNOWN_LANGUAGE):
        lang = code.split(":", 1)[-1]
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message="unknown language",
            failure=FailureReason(
                node_id=node,
                contract_id=cid,
                property_name="language",
                expected="python",
                actual=lang,
                detail="not eval",
            ),
        )
    if code.startswith(BODY_HASH):
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message="artifact body_hash mismatch",
            failure=FailureReason(
                node_id=node,
                contract_id=cid,
                property_name="body_hash",
                expected="artifact.body_hash",
                actual="resolved body",
            ),
        )
    if code.startswith(SOURCE_HASH):
        return ConformanceResult(
            status=ConformanceStatus.FAIL,
            level=ConformanceLevel.STRUCTURAL,
            message="artifact source_hash mismatch",
            failure=FailureReason(
                node_id=node,
                contract_id=cid,
                property_name="source_hash",
                expected="artifact.source_hash",
                actual="file bytes",
            ),
        )
    return ConformanceResult(
        status=ConformanceStatus.FAIL,
        level=ConformanceLevel.STRUCTURAL,
        message="broken artifact reference",
        failure=FailureReason(
            node_id=node,
            contract_id=cid,
            property_name="artifact",
            expected="readable python file+entry",
            actual=code,
        ),
    )
