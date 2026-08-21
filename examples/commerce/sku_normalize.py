"""
Слой A — второй реальный пайплайн: нормализация SKU каталога.

Вход: список «сырых» артикулов (мусор, пробелы, разный регистр, дубли).
Конвейер: clean (str.strip + upper, drop empty/non-str) → dedupe (порядок сохранения).

Тот же контур, что order_amounts:
  ScriptModule (хеш тела) → Leaf → Composite → run_script/Observed
  → check_conformance → plan.lock → PASS | FAIL
"""
from __future__ import annotations

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level2.conformance import check_conformance, explain_result
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.module.composite import CompositeModule
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.state import ExecutionStatus
from acid_engine.level3.script.python_runtime import run_script


def clean_skus(data: list) -> list:
    """Только непустые строки → strip + upper."""
    out = []
    for x in data:
        if type(x) is not str:
            continue
        s = x.strip().upper()
        if s:
            out.append(s)
    return out


def dedupe_preserve_order(data: list) -> list:
    """Убрать дубли, сохранив первый порядок."""
    seen: set[str] = set()
    out = []
    for x in data:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def build_clean_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("commerce", "clean_skus"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200)),
        input_type="list",
        output_type="list",
        implementation=clean_skus,
        name="clean_skus",
    )


def build_dedupe_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("commerce", "dedupe_skus"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200)),
        input_type="list",
        output_type="list",
        implementation=dedupe_preserve_order,
        name="dedupe_skus",
    )


def build_pipeline() -> tuple[CompositeModule, LeafModule, LeafModule]:
    clean_script = build_clean_script()
    dedupe_script = build_dedupe_script()
    leaf_clean = LeafModule(module_id="clean_node", script=clean_script)
    leaf_dedupe = LeafModule(module_id="dedupe_node", script=dedupe_script)

    g = DependencyGraph()
    g.add_node("clean_node", payload=leaf_clean)
    g.add_node("dedupe_node", payload=leaf_dedupe)
    g.add_edge("clean_node", "dedupe_node")

    composite = CompositeModule(
        module_id="sku_normalize_pipe",
        graph=g,
        modules={"clean_node": leaf_clean, "dedupe_node": leaf_dedupe},
        contract_id=ContractId("commerce", "sku_normalize_pipe"),
        version=Version(0, 1, 0),
        input_node="clean_node",
        output_node="dedupe_node",
    )
    return composite, leaf_clean, leaf_dedupe


def run_leaf(leaf: LeafModule, data):
    script = leaf.script
    in_port = PortRef(module=leaf.module_id, direction="input", name="value")
    snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=data,
    )
    out_snap, obs, _delta, state = run_script(script, snap)
    result = check_conformance(
        required_output_type=script.output_type,
        provided_data=out_snap.data,
        obs=obs,
        policy=script.specification.policy,
        node_id=script.name,
        contract_id=str(script.contract_id),
    )
    return out_snap.data, obs, result, state


def make_plan(leaf_clean: LeafModule, leaf_dedupe: LeafModule) -> PlanLock:
    iface = InterfaceContract(
        contract_id=ContractId("commerce", "sku_normalize_iface"),
        version=Version(0, 1, 0),
        inputs={"raw_skus": "list"},
        outputs={"normalized_skus": "list"},
        constraints=leaf_clean.script.specification.policy.to_canonical_dict(),
        module_hashes={
            "clean": leaf_clean.content_hash,
            "dedupe": leaf_dedupe.content_hash,
        },
    )
    return PlanLock.create(
        plan_id="commerce-sku-normalize-001",
        interface_contract_hash=iface.content_hash,
        resolved_policies=iface.constraints,
        module_hashes=iface.module_hashes,
        execution_mode=ExecutionMode.NORMAL,
    )


def main() -> None:
    pipe, leaf_clean, leaf_dedupe = build_pipeline()
    input_data = ["  ab-01 ", "ab-01", "XY-9", 42, "", "  xy-9  ", None, "zz-3"]

    cleaned, obs1, conf1, state1 = run_leaf(leaf_clean, input_data)
    assert state1.status == ExecutionStatus.COMPLETED
    assert conf1.ok, explain_result(conf1)

    deduped, obs2, conf2, state2 = run_leaf(leaf_dedupe, cleaned)
    assert state2.status == ExecutionStatus.COMPLETED
    assert conf2.ok, explain_result(conf2)

    composite_out = pipe.execute(input_data)
    assert composite_out == deduped

    expected = ["AB-01", "XY-9", "ZZ-3"]
    plan = make_plan(leaf_clean, leaf_dedupe)

    print("=== Commerce pipeline: SKU normalize ===")
    print(f"input:    {input_data}")
    print(f"cleaned:  {cleaned}")
    print(f"output:   {deduped}")
    print(f"expected: {expected}")
    print(f"obs1:     status={obs1.status} latency_ms={obs1.latency_ms:.3f}")
    print(f"obs2:     status={obs2.status} latency_ms={obs2.latency_ms:.3f}")
    print(explain_result(conf1))
    print(explain_result(conf2))
    print(f"plan.lock: {plan.content_hash[:16]}...")
    print(f"clean hash:  {leaf_clean.content_hash[:16]}...")
    print(f"dedupe hash: {leaf_dedupe.content_hash[:16]}...")

    assert deduped == expected, f"output mismatch: {deduped} != {expected}"
    assert composite_out == expected
    assert not hasattr(obs2, "proven_pure")
    print("PASS")


if __name__ == "__main__":
    main()
