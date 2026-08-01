"""
Вертикальный use-case: нормализация списка чисел.
Конвейер из двух скриптов: filter (>=0) → scale (/100).
Демонстрирует CompositeModule и полный цикл Required → Provided → PASS.
"""
from __future__ import annotations

from acid_engine.contracts.identity import ContractId, Version
from acid_engine.scripts.specification import Specification, Policy
from acid_engine.scripts.module import ScriptModule
from acid_engine.modules.leaf import LeafModule
from acid_engine.modules.composite import CompositeModule
from acid_engine.graph.model import DependencyGraph
from acid_engine.interface.contract import InterfaceContract
from acid_engine.execution.plan_lock import PlanLock
from acid_engine.execution.modes import ExecutionMode
from acid_engine.contracts.resolver import ConstraintResolver


def build_pipeline():
    # Скрипт 1: фильтр (убираем отрицательные)
    filter_script = ScriptModule(
        contract_id=ContractId("usecase", "filter"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200)),
        input_type="list",
        output_type="list",
        implementation=lambda data: [x for x in data if x >= 0],
        name="filter_non_negative",
    )
    leaf_filter = LeafModule(module_id="filter_node", script=filter_script)

    # Скрипт 2: масштабирование
    scale_script = ScriptModule(
        contract_id=ContractId("usecase", "scale"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=200)),
        input_type="list",
        output_type="list",
        implementation=lambda data: [round(x / 100, 2) for x in data],
        name="scale_down",
    )
    leaf_scale = LeafModule(module_id="scale_node", script=scale_script)

    # Граф: filter → scale
    g = DependencyGraph()
    g.add_node("filter_node", payload=leaf_filter)
    g.add_node("scale_node", payload=leaf_scale)
    g.add_edge("filter_node", "scale_node")

    composite = CompositeModule(
        module_id="normalize_pipe",
        graph=g,
        modules={"filter_node": leaf_filter, "scale_node": leaf_scale},
        contract_id=ContractId("usecase", "normalize_pipe"),
        version=Version(1, 0, 0),
        input_node="filter_node",
        output_node="scale_node",
    )
    return composite


def main():
    pipe = build_pipeline()
    resolver = ConstraintResolver()
    # Для MVP политики всех модулей одинаковы, берём политику первого
    effective_policy = resolver.resolve_policy({}, pipe.modules["filter_node"].script.specification.policy.to_canonical_dict())

    input_data = [150, -10, 0, 250, 50]
    output_data = pipe.execute(input_data)

    # Формируем Interface Contract
    iface = InterfaceContract(
        contract_id=ContractId("usecase", "normalize_iface"),
        version=Version(1, 0, 0),
        inputs={"raw_numbers": "list"},
        outputs={"normalized": "list"},
        constraints=effective_policy,
        module_hashes={
            "filter": pipe.modules["filter_node"].content_hash,
            "scale": pipe.modules["scale_node"].content_hash,
        },
    )

    plan = PlanLock.create(
        plan_id="norm-001",
        interface_contract_hash=iface.content_hash,
        resolved_policies=effective_policy,
        module_hashes=iface.module_hashes,
        execution_mode=ExecutionMode.NORMAL,
    )

    expected = [1.5, 0.0, 2.5, 0.5]
    print("=== Vertical Use-case: Normalize Numbers ===")
    print(f"Input:    {input_data}")
    print(f"Output:   {output_data}")
    print(f"Expected: {expected}")
    print(f"Match:    {output_data == expected}")
    print(f"plan.lock: {plan.content_hash[:16]}...")

    assert output_data == expected, "Pipeline output mismatch"
    print("PASS")


if __name__ == "__main__":
    main()