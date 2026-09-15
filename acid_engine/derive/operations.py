"""Mechanical derive operations: map, filter."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from acid_engine.level2.identity import ContractId
from acid_engine.level3.script.module import ScriptModule


def derive_map(
    source: ScriptModule,
    func: Callable[[Any], Any],
    new_name: str = "mapped",
) -> ScriptModule:
    """
    Build a new ScriptModule that applies func to each list element.
    Contract: list → list; element type is inferred.
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
    Build a ScriptModule that filters a list.
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