"""
Слой A — пайплайн: нормализация SKU каталога.

Вход: сырые артикулы. Конвейер: clean (strip+upper) → dedupe (порядок).
Каждый лист идёт через execute_plan (plan.lock связывает тело).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acid_engine.level2.conformance import check_conformance, explain_result
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.module.composite import CompositeModule
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.python_runtime import run_script
from acid_engine.level3.script.runner import execute_plan


def clean_skus(data: list) -> list:
    out = []
    for x in data:
        if type(x) is not str:
            continue
        s = x.strip().upper()
        if s:
            out.append(s)
    return out


def dedupe_preserve_order(data: list) -> list:
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


def build_pipeline():
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


def lock_pair(leaf_clean: LeafModule, leaf_dedupe: LeafModule):
    iface = InterfaceContract(
        contract_id=ContractId("commerce", "sku_normalize_iface"),
        version=Version(0, 1, 0),
        inputs={"raw_skus": "list"},
        outputs={"normalized_skus": "list"},
        constraints=leaf_clean.script.specification.policy.to_canonical_dict(),
        module_hashes={
            leaf_clean.script.name: leaf_clean.content_hash,
            leaf_dedupe.script.name: leaf_dedupe.content_hash,
        },
    )
    plan = PlanLock.create(
        plan_id="commerce-sku-normalize-001",
        interface_contract_hash=iface.content_hash,
        resolved_policies=iface.constraints,
        module_hashes=iface.module_hashes,
        execution_mode=ExecutionMode.NORMAL,
    )
    return iface, plan


def make_plan(leaf_clean: LeafModule, leaf_dedupe: LeafModule) -> PlanLock:
    return lock_pair(leaf_clean, leaf_dedupe)[1]


def main() -> None:
    pipe, leaf_clean, leaf_dedupe = build_pipeline()
    input_data = ["  ab-01 ", "ab-01", "XY-9", 42, "", "  xy-9  ", None, "zz-3"]
    iface, plan = lock_pair(leaf_clean, leaf_dedupe)

    step1 = execute_plan(iface, plan, leaf_clean.script, input_data)
    assert step1.ok, explain_result(step1.conformance)
    step2 = execute_plan(iface, plan, leaf_dedupe.script, step1.data)
    assert step2.ok, explain_result(step2.conformance)

    composite_out = pipe.execute(input_data, plan=plan, iface=iface).data
    expected = ["AB-01", "XY-9", "ZZ-3"]

    print("=== Commerce pipeline: SKU normalize ===")
    print(f"input:    {input_data}")
    print(f"cleaned:  {step1.data}")
    print(f"output:   {step2.data}")
    print(f"expected: {expected}")
    print(explain_result(step1.conformance))
    print(explain_result(step2.conformance))
    print(f"plan.lock: {plan.content_hash[:16]}...")

    assert step2.data == expected
    assert composite_out == expected
    assert not hasattr(step2.observation, "proven_pure")
    print("PASS")


if __name__ == "__main__":
    main()
