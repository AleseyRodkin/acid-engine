"""Резолв тела: живой callable или ArtifactRef. Чужой язык не eval."""
from __future__ import annotations

import importlib.util
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


def resolve_script(script: Any) -> tuple[Callable[..., Any] | None, str | None]:
    """
    (fn, None) — можно вызывать.
    (None, code) — не исполнять. code: missing_implementation | unknown_language:... | broken_ref:... | body_hash:...
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
        fn = _load_python_entry(path, entry)
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
    """После резолва identity = тело fn. Не резолвится — скрипт как был."""
    from dataclasses import replace

    impl = getattr(script, "implementation", None)
    if callable(impl):
        return script
    fn, _err = resolve_script(script)
    if fn is None:
        return script
    return replace(script, implementation=fn)


def _load_python_entry(path: Path, entry: str) -> Any:
    mod_name = f"acid_artifact_{path.stem}_{abs(hash(str(path.resolve())))}"
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise FileNotFoundError(str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
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
