"""
Self-hosting demo: AcidEngine описывает собственный процесс
канонической сериализации и хеширования через ScriptModule.
Реализация в точности повторяет логику ядра.
"""
from __future__ import annotations

import json
import hashlib
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.scripts.specification import Specification, Policy
from acid_engine.scripts.module import ScriptModule
from acid_engine.scripts.python_runtime import run_script
from acid_engine.containers.port import PortRef
from acid_engine.containers.snapshot import ContainerSnapshot
from acid_engine.contracts.conformance import check_conformance, explain_result
from acid_engine.modules.leaf import LeafModule
from acid_engine.interface.contract import InterfaceContract
from acid_engine.execution.plan_lock import PlanLock
from acid_engine.execution.modes import ExecutionMode


def _normalize(obj):
    """Точная копия _normalize из acid_engine/contracts/serialization.py."""
    if isinstance(obj, dict):
        return {k: _normalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, (list, tuple)):
        return [_normalize(x) for x in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if obj == 0.0:
            return 0.0
        return float(obj)
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if hasattr(obj, "to_canonical_dict"):
        return _normalize(obj.to_canonical_dict())
    if hasattr(obj, "__dict__"):
        return _normalize(
            {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        )
    raise TypeError(f"Cannot normalize type {type(obj)!r}")


def _canonical_serialize(data) -> str:
    """Точная копия canonical_serialize."""
    normalized = _normalize(data)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def _hash_data(data) -> str:
    """Вычисление хеша как в ядре: SHA-256 от канонической формы."""
    canonical = _canonical_serialize(data)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main():
    script = ScriptModule(
        contract_id=ContractId("self", "canonical_hash"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(pure=True)),
        input_type="dict",
        output_type="str",
        implementation=lambda d: _hash_data(d),
        name="self_canonical_hash",
    )
    leaf = LeafModule(module_id="hash_node", script=script)

    input_data = {"z": 1, "a": [3, 2]}
    in_port = PortRef("self", "input", "value")
    input_snap = ContainerSnapshot.create(
        in_port, script.contract_id, script.content_hash, input_data
    )

    out_snap, obs, delta, state = run_script(script, input_snap)
    result = check_conformance(
        "str", out_snap.data, obs, script.specification.policy,
        node_id=script.name, contract_id=str(script.contract_id),
    )

    iface = InterfaceContract(
        contract_id=ContractId("self", "hash_iface"),
        version=Version(1, 0, 0),
        inputs={"raw": "dict"},
        outputs={"hash": "str"},
        constraints={"pure": True},
        module_hashes={leaf.module_id: leaf.content_hash},
    )
    plan = PlanLock.create(
        "hash-001", iface.content_hash, {"pure": True},
        iface.module_hashes, ExecutionMode.NORMAL,
    )

    print("=== Self-Hosting: Canonical Hash ===")
    print(f"Input:     {input_data}")
    print(f"Hash:      {out_snap.data}")
    print(f"Conformance: {explain_result(result)}")
    print(f"plan.lock: {plan.content_hash[:16]}...")

    # Сравнение с ядром
    from acid_engine.contracts.serialization import canonical_serialize, content_hash_of
    expected_hash = content_hash_of(input_data)
    assert out_snap.data == expected_hash, f"Hash mismatch: {out_snap.data} vs {expected_hash}"
    print("PASS (matches core canonical hash)")


if __name__ == "__main__":
    main()