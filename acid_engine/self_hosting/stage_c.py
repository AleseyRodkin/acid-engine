"""
Stage C Self-Hosting: ключевые компоненты AcidEngine описаны как ScriptModule,
собраны в граф, и их конформность проверяется ядром же.
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


def _canonicalize_and_hash(data: dict) -> str:
    """Реализация identity + serialization: хеш от канонической формы."""
    from acid_engine.contracts.serialization import canonical_serialize, content_hash_of
    return content_hash_of(data)


def _identity(data: str) -> str:
    """Просто возвращает вход (имитация раннера)."""
    return data


def build_self_hosted_graph() -> CompositeModule:
    """
    Строит граф: serialization → identity.
    """
    # Компонент 1: каноническая сериализация + хеш
    ser_script = ScriptModule(
        contract_id=ContractId("acid.self", "serialize_hash"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(pure=True)),
        input_type="dict",
        output_type="str",
        implementation=_canonicalize_and_hash,
        name="serialize_hash",
    )
    leaf_ser = LeafModule(module_id="serialize_hash", script=ser_script)

    # Компонент 2: identity (заглушка вместо resolver)
    identity_script = ScriptModule(
        contract_id=ContractId("acid.self", "identity"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(pure=True)),
        input_type="str",
        output_type="str",
        implementation=_identity,
        name="identity",
    )
    leaf_identity = LeafModule(module_id="identity", script=identity_script)

    # Граф: serialization → identity
    g = DependencyGraph()
    g.add_node("serialize_hash", payload=leaf_ser)
    g.add_node("identity", payload=leaf_identity)
    g.add_edge("serialize_hash", "identity")

    composite = CompositeModule(
        module_id="acid_self_core",
        graph=g,
        modules={
            "serialize_hash": leaf_ser,
            "identity": leaf_identity,
        },
        contract_id=ContractId("acid.self", "core_pipeline"),
        version=Version(1, 0, 0),
        input_node="serialize_hash",
        output_node="identity",
    )
    return composite