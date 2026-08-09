"""Pipeline — замкнутый контур выполнения контракта (уровень 3)."""
from __future__ import annotations

from typing import Any, Optional
from acid_engine.level2.base import Contract
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.module.composite import CompositeModule
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.script.python_runtime import run_script
from acid_engine.level2.conformance import check_conformance, ConformanceResult
from acid_engine.level2.specification import Policy
from acid_engine.level2.specification import Specification  # уже там
import time


class Pipeline:
    """Замкнутый контур выполнения: контракт → модуль → граф → проверка."""

    def __init__(self, contract: Contract, registry: Optional[Any] = None):
        self.contract = contract
        self.registry = registry

    def execute(self, input_data: Any) -> ConformanceResult:
        """
        Выполняет контракт и возвращает результат конформности.
        Если contract — это ScriptModule, выполняется он.
        Если InterfaceContract — строится граф и выполняется CompositeModule.
        """
        # Определяем тип контракта и создаём модуль
        if isinstance(self.contract, ScriptModule):
            module = LeafModule(
                module_id=self.contract.contract_id.name,
                script=self.contract
            )
            # Выполняем через run_script напрямую
            in_port = PortRef(module=self.contract.contract_id.name, direction="input", name="value")
            input_snap = ContainerSnapshot.create(
                port_ref=in_port,
                contract_id=self.contract.contract_id,
                contract_hash=self.contract.content_hash,
                data=input_data,
            )
            start = time.perf_counter()
            output_snap, obs, delta, state = run_script(self.contract, input_snap)
            end = time.perf_counter()
            # Строим политику из спецификации
            policy = self.contract.specification.policy if hasattr(self.contract.specification, 'policy') else Policy()
            result = check_conformance(
                required_output_type=self.contract.output_type,
                provided_data=output_snap.data,
                obs=obs,
                policy=policy,
                node_id=self.contract.name,
                contract_id=str(self.contract.contract_id),
            )
            return result

        elif isinstance(self.contract, InterfaceContract):
            # Пока минимальная реализация: создаём заглушку модуля и возвращаем PASS
            # В будущем здесь будет построение графа из module_hashes и их выполнение
            from acid_engine.level2.conformance import ConformanceStatus, ConformanceLevel
            return ConformanceResult(
                status=ConformanceStatus.PASS,
                level=ConformanceLevel.STRUCTURAL,
                message="InterfaceContract executed (stub)"
            )

        else:
            raise TypeError(f"Unsupported contract type: {type(self.contract)}")