"""Bones blank: JSON-safe identity without a callable and without content_hash inside identity."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from acid_engine.level2.serialization import content_hash_of

SCHEMA_SCRIPT = "acid.blank.script.v1"

_SCRIPT_IDENTITY_KEYS = frozenset(
    {
        "contract_id",
        "version",
        "specification",
        "input_type",
        "output_type",
        "name",
        "implementation",
    }
)
_CONTAINER_KEYS = frozenset(
    {
        "port_ref",
        "contract_id",
        "contract_hash",
        "content_hash",
        "cardinality",
        "provenance",
        "data",
    }
)
_ENVELOPE_KEYS = frozenset({"schema", "kind", "identity"})


def script_identity_blank(script: Any) -> dict[str, Any]:
    """Script identity = `_identity_dict` (no content_hash). The hash matches."""
    ident: dict[str, Any] = script._identity_dict()
    return ident


def script_identity_envelope(script: Any) -> dict[str, Any]:
    """Wrapper. schema/kind are not in the identity content_hash."""
    return {
        "schema": SCHEMA_SCRIPT,
        "kind": "script",
        "identity": script_identity_blank(script),
    }


def parse_script_identity_blank(obj: Mapping[str, Any]) -> dict[str, Any]:
    """Parse identity or an envelope {schema,kind,identity}. Unknown key is an error."""
    if not isinstance(obj, Mapping):
        raise TypeError(f"script blank must be a mapping, got {type(obj)!r}")
    data = dict(obj)
    if "identity" in data:
        extra = set(data) - _ENVELOPE_KEYS
        if extra:
            raise ValueError(f"unknown key: {sorted(extra)[0]}")
        ident = data["identity"]
        if not isinstance(ident, Mapping):
            raise TypeError("identity must be a mapping")
        ident = dict(ident)
    else:
        ident = data
    extra = set(ident) - _SCRIPT_IDENTITY_KEYS
    if extra:
        raise ValueError(f"unknown key: {sorted(extra)[0]}")
    out: dict[str, Any] = dict(ident)
    return out


def container_blank(snapshot: Any) -> dict[str, Any]:
    """JSON-safe snapshot including data. Without data a step cannot be built from a blank."""
    return {
        "port_ref": str(snapshot.port_ref),
        "contract_id": str(snapshot.contract_id),
        "contract_hash": snapshot.contract_hash,
        "content_hash": snapshot.content_hash,
        "cardinality": snapshot.cardinality,
        "provenance": snapshot.provenance,
        "data": snapshot.data,
    }


def parse_container_blank(obj: Mapping[str, Any]) -> Any:
    """Build ContainerSnapshot from a blank. content_hash must match data."""
    from acid_engine.level2.identity import ContractId
    from acid_engine.level3.container.port import PortRef
    from acid_engine.level3.container.snapshot import ContainerSnapshot

    if not isinstance(obj, Mapping):
        raise TypeError(f"container blank must be a mapping, got {type(obj)!r}")
    extra = set(obj) - _CONTAINER_KEYS
    if extra:
        raise ValueError(f"unknown key: {sorted(extra)[0]}")
    if "data" not in obj:
        raise ValueError("container blank without data cannot rebuild a step")
    snap = ContainerSnapshot.create(
        port_ref=PortRef.parse(str(obj["port_ref"])),
        contract_id=ContractId.parse(str(obj["contract_id"])),
        contract_hash=str(obj["contract_hash"]),
        data=obj["data"],
        cardinality=int(obj.get("cardinality", 1)),
        provenance=str(obj.get("provenance") or ""),
    )
    expected = str(obj["content_hash"])
    if snap.content_hash != expected:
        raise ValueError("container blank content_hash does not match data")
    return snap


def plan_blank(plan: Any) -> dict[str, Any]:
    """Lock body without created_at (it is not in the PlanLock hash)."""
    return {
        "plan_id": plan.plan_id,
        "interface_contract_hash": plan.interface_contract_hash,
        "resolved_policies": plan.resolved_policies,
        "module_hashes": dict(plan.module_hashes),
        "execution_mode": plan.execution_mode.value
        if hasattr(plan.execution_mode, "value")
        else str(plan.execution_mode),
    }


def graph_blank(graph: Any) -> dict[str, Any]:
    """Nodes and edges without payload (a callable is not serialized)."""
    return {
        "nodes": sorted(graph.nodes.keys()),
        "edges": [
            {"source": e.source, "target": e.target} for e in graph.edges
        ],
    }


def observation_blank(obs: Any) -> dict[str, Any]:
    """Run fact. run_id is not included — it identifies the record, not the script."""
    return {
        "status": obs.status,
        "latency_ms": obs.latency_ms,
        "effects_observed": list(obs.effects_observed),
        "trace": list(obs.trace),
        "input_hash": obs.input_hash,
        "output_hash": obs.output_hash,
    }


def conformance_blank(result: Any) -> dict[str, Any]:
    failure = None
    if result.failure is not None:
        f = result.failure
        failure = {
            "node_id": f.node_id,
            "contract_id": f.contract_id,
            "property_name": f.property_name,
            "expected": f.expected,
            "actual": f.actual,
            "detail": f.detail,
        }
    status = result.status.value if hasattr(result.status, "value") else str(result.status)
    level = result.level.value if hasattr(result.level, "value") else str(result.level)
    return {
        "status": status,
        "level": level,
        "message": result.message,
        "failure": failure,
    }


def blank_hash(blank: Mapping[str, Any]) -> str:
    return content_hash_of(dict(blank))
