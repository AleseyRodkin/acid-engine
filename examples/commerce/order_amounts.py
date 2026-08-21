"""
Слой A — первый реальный пайплайн: нормализация сумм строк заказа.

Вход: список сумм в минорных единицах (копейки/центы), возможны мусор и отрицательные.
Конвейер: filter (>=0, число) → scale (/100 → major units).

Полный контур:
  ScriptModule (хеш тела) → Leaf → Composite (линейный) → run_script/Observed
  → check_conformance → plan.lock → PASS | FAIL
Заглушка Interface без исполнения не используется как успех.
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
from acid_engine.level3.script.python_runtime import run_script


def filter_non_negative(data: list) -> list:
    """Оставить только числа >= 0. bool не число."""
    out = []
    for x in data:
        if type(x) is bool:
            continue
        if type(x) in (int, float) and x >= 0:
            out.append(x)
    return out


def scale_cents_to_units(data: list) -> list:
    """Минорные единицы → major ( / 100 ), 2 знака."""
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


def build_pipeline() -> tuple[CompositeModule, LeafModule, LeafModule]:
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
    """Исполнение листа с Observed и conformance."""
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


def make_plan(leaf_filter: LeafModule, leaf_scale: LeafModule) -> PlanLock:
    iface = InterfaceContract(
        contract_id=ContractId("commerce", "order_amounts_iface"),
        version=Version(0, 1, 0),
        inputs={"raw_amounts": "list"},
        outputs={"normalized": "list"},
        constraints=leaf_filter.script.specification.policy.to_canonical_dict(),
        module_hashes={
            "filter": leaf_filter.content_hash,
            "scale": leaf_scale.content_hash,
        },
    )
    return PlanLock.create(
        plan_id="commerce-order-amounts-001",
        interface_contract_hash=iface.content_hash,
        resolved_policies=iface.constraints,
        module_hashes=iface.module_hashes,
        execution_mode=ExecutionMode.NORMAL,
    )


def main() -> None:
    pipe, leaf_filter, leaf_scale = build_pipeline()
    input_data = [15000, -200, 0, True, 25050, 100]

    # Шаг 1: filter с observation
    filtered, obs1, conf1, state1 = run_leaf(leaf_filter, input_data)
    from acid_engine.level3.container.state import ExecutionStatus
    assert state1.status == ExecutionStatus.COMPLETED
    assert conf1.ok, explain_result(conf1)

    # Шаг 2: scale с observation
    scaled, obs2, conf2, state2 = run_leaf(leaf_scale, filtered)
    assert conf2.ok, explain_result(conf2)

    # Composite (линейный путь, fan-in=1)
    composite_out = pipe.execute(input_data)
    assert composite_out == scaled

    expected = [150.0, 0.0, 250.5, 1.0]
    plan = make_plan(leaf_filter, leaf_scale)

    print("=== Commerce pipeline: order amounts ===")
    print(f"input:     {input_data}")
    print(f"filtered:  {filtered}")
    print(f"output:    {scaled}")
    print(f"expected:  {expected}")
    print(f"obs1:      status={obs1.status} latency_ms={obs1.latency_ms:.3f}")
    print(f"obs2:      status={obs2.status} latency_ms={obs2.latency_ms:.3f}")
    print(explain_result(conf1))
    print(explain_result(conf2))
    print(f"plan.lock: {plan.content_hash[:16]}...")
    print(f"filter hash: {leaf_filter.content_hash[:16]}...")
    print(f"scale hash:  {leaf_scale.content_hash[:16]}...")

    assert scaled == expected, f"output mismatch: {scaled} != {expected}"
    assert composite_out == expected
    # Observed ≠ Proven: pure=True в policy, но proven_pure нет
    assert not hasattr(obs2, "proven_pure")
    print("PASS")


if __name__ == "__main__":
    main()
