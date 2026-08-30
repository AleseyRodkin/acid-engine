"""Бланк костей: JSON-safe identity без callable и без content_hash внутри identity."""
from __future__ import annotations

from typing import Any, Mapping

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
_ENVELOPE_KEYS = frozenset({"schema", "kind", "identity"})


def script_identity_blank(script) -> dict[str, Any]:
    """Identity скрипта = `_identity_dict` (без content_hash). Хеш совпадает."""
    return script._identity_dict()


def script_identity_envelope(script) -> dict[str, Any]:
    """Обёртка. schema/kind не входят в content_hash identity."""
    return {
        "schema": SCHEMA_SCRIPT,
        "kind": "script",
        "identity": script_identity_blank(script),
    }


def parse_script_identity_blank(obj: Mapping[str, Any]) -> dict[str, Any]:
    """Разобрать identity или конверт {schema,kind,identity}. Неизвестный ключ — ошибка."""
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
    return ident


def container_blank(snapshot) -> dict[str, Any]:
    return {
        "port_ref": str(snapshot.port_ref),
        "contract_id": str(snapshot.contract_id),
        "contract_hash": snapshot.contract_hash,
        "content_hash": snapshot.content_hash,
        "cardinality": snapshot.cardinality,
        "provenance": snapshot.provenance,
    }


def plan_blank(plan) -> dict[str, Any]:
    """Тело замка без created_at (он не входит в хеш PlanLock)."""
    return {
        "plan_id": plan.plan_id,
        "interface_contract_hash": plan.interface_contract_hash,
        "resolved_policies": plan.resolved_policies,
        "module_hashes": dict(plan.module_hashes),
        "execution_mode": plan.execution_mode.value
        if hasattr(plan.execution_mode, "value")
        else str(plan.execution_mode),
    }


def graph_blank(graph) -> dict[str, Any]:
    """Узлы и рёбра без payload (callable не сериализуется)."""
    return {
        "nodes": sorted(graph.nodes.keys()),
        "edges": [
            {"source": e.source, "target": e.target} for e in graph.edges
        ],
    }


def observation_blank(obs) -> dict[str, Any]:
    """Факт прогона. run_id не входит — это идентификатор записи, не identity скрипта."""
    return {
        "status": obs.status,
        "latency_ms": obs.latency_ms,
        "effects_observed": list(obs.effects_observed),
        "trace": list(obs.trace),
        "input_hash": obs.input_hash,
        "output_hash": obs.output_hash,
    }


def conformance_blank(result) -> dict[str, Any]:
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
