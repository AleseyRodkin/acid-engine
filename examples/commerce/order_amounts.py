"""
Слой A — пайплайн: нормализация сумм строк заказа.

Вход: список сумм в минорных единицах (копейки/центы).
Конвейер: filter (>=0, число; bool не число) → scale (/100 → major units).
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


def filter_non_negative(data: list) -> list:
    out = []
    for x in data:
        if type(x) is bool:
            continue
        if type(x) in (int, float) and x >= 0:
            out.append(x)
    return out


def scale_cents_to_units(data: list) -> list:
    return [round(x / 100.0, 2) for x in data]


def build_filter_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("commerce", "filter_amounts"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200)),
        input_type="list",
        output_type="list",
        implementation=filter_non_negative,
        name="filter_amounts",
    )


def build_scale_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("commerce", "scale_amounts"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200)),
        input_type="list",
        output_type="list",
        implementation=scale_cents_to_units,
        name="scale_amounts",
    )


def build_pipeline():
    filter_script = build_filter_script()
    scale_script = build_scale_script()
    leaf_filter = LeafModule(module_id="filter_node", script=filter_script)
    leaf_scale = LeafModule(module_id="scale_node", script=scale_script)

    g = DependencyGraph()
    g.add_node("filter_node", payload=leaf_filter)
    g.add_node("scale_node", payload=leaf_scale)
    g.add_edge("filter_node", "scale_node")

    composite = CompositeModule(
        module_id="order_amounts_pipe",
        graph=g,
        modules={"filter_node": leaf_filter, "scale_node": leaf_scale},
        contract_id=ContractId("commerce", "order_amounts_pipe"),
        version=Version(0, 1, 0),
        input_node="filter_node",
        output_node="scale_node",
    )
    return composite, leaf_filter, leaf_scale


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


def lock_pair(leaf_filter: LeafModule, leaf_scale: LeafModule):
    iface = InterfaceContract(
        contract_id=ContractId("commerce", "order_amounts_iface"),
        version=Version(0, 1, 0),
        inputs={"raw_amounts": "list"},
        outputs={"normalized": "list"},
        constraints=leaf_filter.script.specification.policy.to_canonical_dict(),
        module_hashes={
            leaf_filter.script.name: leaf_filter.content_hash,
            leaf_scale.script.name: leaf_scale.content_hash,
        },
    )
    plan = PlanLock.create(
        plan_id="commerce-order-amounts-001",
        interface_contract_hash=iface.content_hash,
        resolved_policies=iface.constraints,
        module_hashes=iface.module_hashes,
        execution_mode=ExecutionMode.NORMAL,
    )
    return iface, plan


def make_plan(leaf_filter: LeafModule, leaf_scale: LeafModule) -> PlanLock:
    return lock_pair(leaf_filter, leaf_scale)[1]


def main() -> None:
    pipe, leaf_filter, leaf_scale = build_pipeline()
    input_data = [15000, -200, 0, True, 25050, 100]
    iface, plan = lock_pair(leaf_filter, leaf_scale)

    step1 = execute_plan(iface, plan, leaf_filter.script, input_data)
    assert step1.ok, explain_result(step1.conformance)
    assert step1.observation is not None

    step2 = execute_plan(iface, plan, leaf_scale.script, step1.data)
    assert step2.ok, explain_result(step2.conformance)
    assert step2.observation is not None

    composite_out = pipe.execute(input_data, plan=plan, iface=iface).data
    assert composite_out == step2.data

    expected = [150.0, 0.0, 250.5, 1.0]

    print("=== Commerce pipeline: order amounts ===")
    print(f"input:     {input_data}")
    print(f"filtered:  {step1.data}")
    print(f"output:    {step2.data}")
    print(f"expected:  {expected}")
    print(explain_result(step1.conformance))
    print(explain_result(step2.conformance))
    print(f"plan.lock: {plan.content_hash[:16]}...")

    assert step2.data == expected
    assert composite_out == expected
    assert not hasattr(step2.observation, "proven_pure")
    print("PASS")


if __name__ == "__main__":
    main()
