"""Load a step from JSON handwriting. Markdown and YAML are not parsed."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from acid_engine.level2.blank import SCHEMA_SCRIPT
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.implementation_canon import canonical_implementation
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level2.specification import (
    ImplementationRequirements,
    Parameters,
    Policy,
    Specification,
)
from acid_engine.level3.script.artifact import CANON_KINDS, ArtifactRef
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.resolve import _load_python_entry

_AUTHORING_KEYS = frozenset(
    {
        "schema",
        "kind",
        "contract_id",
        "version",
        "name",
        "input_type",
        "output_type",
        "specification",
        "implementation",
    }
)
_IMPL_KEYS = frozenset({"language", "file", "entry", "canon", "body_hash", "source_hash"})


def load_script_blank(path: str | Path) -> ScriptModule:
    source = Path(path)
    if source.suffix.lower() == ".md":
        raise ValueError("markdown specs are not parsed")
    if source.suffix.lower() != ".json":
        raise ValueError(f"blank loader expects .json, got: {source}")
    from acid_engine.level2.local_deps import read_source_bytes

    data = json.loads(read_source_bytes(source).decode("utf-8"))
    if not isinstance(data, dict):
        raise TypeError("script blank JSON must be an object")
    return script_from_authoring_dict(data, base_dir=source.parent)


def script_from_authoring_dict(
    data: Mapping[str, Any],
    *,
    base_dir: Path | None = None,
) -> ScriptModule:
    extra = set(data) - _AUTHORING_KEYS
    if extra:
        raise ValueError(f"unknown key: {sorted(extra)[0]}")

    schema = data.get("schema")
    if schema is not None and schema != SCHEMA_SCRIPT:
        raise ValueError(f"unknown schema: {schema!r}")
    kind = data.get("kind")
    if kind is not None and kind != "script":
        raise ValueError(f"unknown kind: {kind!r}")

    cid_raw = data.get("contract_id")
    if not cid_raw:
        raise ValueError("contract_id is required")
    contract_id = ContractId.parse(str(cid_raw))

    version = _parse_version(str(data.get("version") or "0.1.0"))
    name = str(data.get("name") or contract_id.name)
    input_type = str(data.get("input_type") or "int")
    output_type = str(data.get("output_type") or "int")
    specification = _spec_from_dict(data.get("specification"))

    impl_raw = data.get("implementation")
    if not isinstance(impl_raw, Mapping):
        raise ValueError("implementation must be {language,file,entry}")
    extra_impl = set(impl_raw) - _IMPL_KEYS
    if extra_impl:
        raise ValueError(f"unknown key: {sorted(extra_impl)[0]}")

    language = str(impl_raw.get("language") or "")
    file_s = str(impl_raw.get("file") or "")
    entry = str(impl_raw.get("entry") or "")
    body_hash = str(impl_raw.get("body_hash") or "")
    source_hash = str(impl_raw.get("source_hash") or "")
    canon = str(impl_raw.get("canon") or "ast")
    if canon not in CANON_KINDS:
        raise ValueError(f"canon must be one of {sorted(CANON_KINDS)}, got {canon!r}")

    path = Path(file_s)
    if not path.is_absolute() and base_dir is not None:
        path = (base_dir / path).resolve()

    artifact = ArtifactRef(
        language=language or "python",
        file=str(path) if file_s else file_s,
        entry=entry,
        canon=canon,
        body_hash=body_hash,
        source_hash=source_hash,
    )

    fn = None
    if language.strip().lower() == "python" and file_s and entry:
        if not path.is_file():
            raise FileNotFoundError(str(path))
        from acid_engine.level2.local_deps import pin_source_bytes, read_source_bytes

        src = read_source_bytes(path)
        file_digest = hashlib.sha256(src).hexdigest()
        if source_hash and source_hash != file_digest:
            raise ValueError("source_hash mismatch")
        pin_source_bytes(path, src)
        fn = _load_python_entry(
            path,
            entry,
            expected_body_hash=body_hash,
            expected_source_hash=source_hash or file_digest,
        )
        if not callable(fn):
            raise TypeError(f"entry {entry!r} is not callable")
        actual = content_hash_of(canonical_implementation(fn))
        if body_hash and actual != body_hash:
            raise ValueError("body_hash does not match resolved implementation")
        if not body_hash or not source_hash:
            from acid_engine.level2.local_deps import read_source_bytes

            file_digest = hashlib.sha256(read_source_bytes(path)).hexdigest()
            artifact = ArtifactRef(
                language="python",
                file=str(path),
                entry=entry,
                canon=canonical_implementation(fn).get("kind", canon),
                body_hash=body_hash or actual,
                source_hash=source_hash or file_digest,
            )

    return ScriptModule(
        contract_id=contract_id,
        version=version,
        specification=specification,
        input_type=input_type,
        output_type=output_type,
        implementation=fn,
        name=name,
        artifact=artifact,
    )


def _parse_version(s: str) -> Version:
    label = ""
    if "-" in s:
        s, label = s.split("-", 1)
    nums = s.split(".")
    major = int(nums[0]) if nums else 0
    minor = int(nums[1]) if len(nums) > 1 else 0
    patch = int(nums[2]) if len(nums) > 2 else 0
    return Version(major, minor, patch, label)


def _spec_from_dict(raw: Any) -> Specification:
    if not raw:
        return Specification()
    if not isinstance(raw, Mapping):
        raise TypeError("specification must be an object")
    pol = raw.get("policy") or {}
    latency = pol.get("max_latency_ms")
    if latency is not None:
        latency = float(latency)
    gate = pol.get("quality_gate")
    if gate is not None:
        gate = float(gate)
    policy = Policy(
        pure=bool(pol.get("pure", False)),
        max_latency_ms=latency,
        history=str(pol.get("history", "none")),
        network=str(pol.get("network", "forbidden")),
        security=str(pol.get("security", "restricted")),
        quality_gate=gate,
    )
    params_raw = raw.get("parameters") or {}
    values = dict(params_raw.get("values") or {})
    ireq = raw.get("implementation_requirements") or {}
    req = ImplementationRequirements(
        required_methods=tuple(ireq.get("required_methods") or ()),
        required_exports=tuple(ireq.get("required_exports") or ()),
        required_signatures=tuple(ireq.get("required_signatures") or ()),
    )
    return Specification(
        parameters=Parameters(values=values),
        policy=policy,
        implementation_requirements=req,
    )
