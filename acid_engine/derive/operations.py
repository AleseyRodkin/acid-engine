"""Mechanical derive operations: map, filter."""
from __future__ import annotations

from typing import Any, Callable
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level3.script.specification import Specification


def derive_map(
    source: ScriptModule,
    func: Callable[[Any], Any],
    new_name: str = "mapped",
) -> ScriptModule:
    """
    Создаёт новый ScriptModule, применяющий func к каждому элементу списка.
    Контракт: list → list, тип элементов определяется автоматически.
    """
    return ScriptModule(
        contract_id=ContractId(source.contract_id.namespace, f"{source.contract_id.name}_{new_name}"),
        version=source.version,
        specification=source.specification,
        input_type=source.input_type,
        output_type=source.output_type,
        implementation=lambda data: [func(x) for x in data],
        name=f"{source.name}_map_{new_name}",
    )


def derive_filter(
    source: ScriptModule,
    predicate: Callable[[Any], bool],
    new_name: str = "filtered",
) -> ScriptModule:
    """
    Создаёт ScriptModule с фильтрацией списка.
    """
    return ScriptModule(
        contract_id=ContractId(source.contract_id.namespace, f"{source.contract_id.name}_{new_name}"),
        version=source.version,
        specification=source.specification,
        input_type=source.input_type,
        output_type=source.output_type,
        implementation=lambda data: [x for x in data if predicate(x)],
        name=f"{source.name}_filter_{new_name}",
    )