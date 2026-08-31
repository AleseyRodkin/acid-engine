"""Минимальная система миграции контрактов."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from acid_engine.level2.compatibility import CompatibilityKind, compare_types
from acid_engine.level3.interface.contract import InterfaceContract


class MigrationAction(str, Enum):
    ADD_FIELD = "add_field"
    REMOVE_FIELD = "remove_field"
    CHANGE_TYPE = "change_type"
    NOOP = "noop"


@dataclass(frozen=True, slots=True)
class MigrationStep:
    action: MigrationAction
    target: str            # "inputs.x", "outputs.y", "constraints.z"
    old_value: Any | None = None
    new_value: Any | None = None
    reversible: bool = True
    note: str = ""


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    old_hash: str
    new_hash: str
    steps: tuple[MigrationStep, ...] = field(default_factory=tuple)

    @property
    def is_breaking(self) -> bool:
        return any(
            s.action == MigrationAction.CHANGE_TYPE
            for s in self.steps
        )

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "steps": [
                {
                    "action": s.action.value,
                    "target": s.target,
                    "old_value": s.old_value,
                    "new_value": s.new_value,
                    "reversible": s.reversible,
                    "note": s.note,
                }
                for s in self.steps
            ],
        }


def plan_migration(old: InterfaceContract, new: InterfaceContract) -> MigrationPlan:
    """Строит план миграции между двумя версиями InterfaceContract."""
    steps: list[MigrationStep] = []

    # Сравниваем inputs
    all_input_keys = set(old.inputs.keys()) | set(new.inputs.keys())
    for k in all_input_keys:
        old_type = old.inputs.get(k)
        new_type = new.inputs.get(k)
        if old_type is None and new_type is not None:
            steps.append(MigrationStep(
                action=MigrationAction.ADD_FIELD,
                target=f"inputs.{k}",
                new_value=new_type,
            ))
        elif old_type is not None and new_type is None:
            steps.append(MigrationStep(
                action=MigrationAction.REMOVE_FIELD,
                target=f"inputs.{k}",
                old_value=old_type,
            ))
        elif old_type is not None and new_type is not None and old_type != new_type:
            compat = compare_types(old_type, new_type)
            steps.append(MigrationStep(
                action=MigrationAction.CHANGE_TYPE,
                target=f"inputs.{k}",
                old_value=old_type,
                new_value=new_type,
                reversible=compat.kind != CompatibilityKind.BREAKING,
                note=compat.message,
            ))

    # Сравниваем outputs
    all_output_keys = set(old.outputs.keys()) | set(new.outputs.keys())
    for k in all_output_keys:
        old_type = old.outputs.get(k)
        new_type = new.outputs.get(k)
        if old_type is None and new_type is not None:
            steps.append(MigrationStep(
                action=MigrationAction.ADD_FIELD,
                target=f"outputs.{k}",
                new_value=new_type,
            ))
        elif old_type is not None and new_type is None:
            steps.append(MigrationStep(
                action=MigrationAction.REMOVE_FIELD,
                target=f"outputs.{k}",
                old_value=old_type,
            ))
        elif old_type is not None and new_type is not None and old_type != new_type:
            compat = compare_types(old_type, new_type)
            steps.append(MigrationStep(
                action=MigrationAction.CHANGE_TYPE,
                target=f"outputs.{k}",
                old_value=old_type,
                new_value=new_type,
                reversible=compat.kind != CompatibilityKind.BREAKING,
                note=compat.message,
            ))

    # Сравниваем constraints (пока просто фиксируем изменения)
    all_constraint_keys = set(old.constraints.keys()) | set(new.constraints.keys())
    for k in all_constraint_keys:
        old_val = old.constraints.get(k)
        new_val = new.constraints.get(k)
        if old_val is None and new_val is not None:
            steps.append(MigrationStep(
                action=MigrationAction.ADD_FIELD,
                target=f"constraints.{k}",
                new_value=new_val,
            ))
        elif old_val is not None and new_val is None:
            steps.append(MigrationStep(
                action=MigrationAction.REMOVE_FIELD,
                target=f"constraints.{k}",
                old_value=old_val,
            ))
        elif old_val != new_val:
            steps.append(MigrationStep(
                action=MigrationAction.CHANGE_TYPE,
                target=f"constraints.{k}",
                old_value=old_val,
                new_value=new_val,
                note="Constraint value changed",
            ))

    return MigrationPlan(
        old_hash=old.content_hash,
        new_hash=new.content_hash,
        steps=tuple(steps),
    )