"""Self-description: AcidEngine описывает собственные контракты."""
from __future__ import annotations

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.module.composite import CompositeModule
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.script.module import ScriptModule


def _dummy_script(name: str, inp: str, out: str) -> ScriptModule:
    """Создаёт заглушку ScriptModule для самоописания."""
    return ScriptModule(
        contract_id=ContractId("acid_engine.self", name),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(pure=True)),
        input_type=inp,
        output_type=out,
        implementation=lambda x: x,
        name=name,
    )


def build_self_contract() -> InterfaceContract:
    """
    Строит InterfaceContract, описывающий само ядро AcidEngine.
    Представляет ключевые операции как модули в графе.
    """
    # Описываем компоненты как скрипты (условно)
    identity_script = _dummy_script("identity", "dict", "dict")
    serialization_script = _dummy_script("serialization", "any", "str")
    resolver_script = _dummy_script("resolver", "policy", "policy")
    runner_script = _dummy_script("runner", "container", "container")

    leaf_identity = LeafModule("identity", identity_script)
    leaf_serial = LeafModule("serialization", serialization_script)
    leaf_resolver = LeafModule("resolver", resolver_script)
    leaf_runner = LeafModule("runner", runner_script)

    # Строим граф зависимостей
    g = DependencyGraph()
    for n in ["identity", "serialization", "resolver", "runner"]:
        g.add_node(n)
    g.add_edge("identity", "serialization")   # сериализация зависит от identity
    g.add_edge("serialization", "resolver")    # resolver использует сериализацию
    g.add_edge("resolver", "runner")           # runner использует resolver

    modules = {
        "identity": leaf_identity,
        "serialization": leaf_serial,
        "resolver": leaf_resolver,
        "runner": leaf_runner,
    }
    composite = CompositeModule(
        module_id="acid_core",
        graph=g,
        modules=modules,
        contract_id=ContractId("acid_engine.self", "core"),
        version=Version(1, 0, 0),
        input_node="identity",
        output_node="runner",
    )

    iface = InterfaceContract(
        contract_id=ContractId("acid_engine.self", "core_iface"),
        version=Version(1, 0, 0),
        inputs={"raw_data": "any"},
        outputs={"processed": "container"},
        constraints={"pure": True},
        capabilities=["contract_identity", "canonical_serialization", "constraint_resolution", "script_execution"],
        module_hashes={
            n: composite.modules[n].content_hash for n in modules
        },
    )
    return iface