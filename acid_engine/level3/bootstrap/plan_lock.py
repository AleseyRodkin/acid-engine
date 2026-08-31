"""Immutable plan.lock."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from acid_engine.level2.serialization import content_hash_of
from acid_engine.level3.script.modes import ExecutionMode


@dataclass(frozen=True, slots=True)
class PlanLock:
    plan_id: str
    created_at: float
    interface_contract_hash: str
    resolved_policies: dict[str, Any]
    module_hashes: dict[str, str]
    execution_mode: ExecutionMode
    content_hash: str

    @staticmethod
    def create(
        plan_id: str,
        interface_contract_hash: str,
        resolved_policies: dict[str, Any],
        module_hashes: dict[str, str],
        execution_mode: ExecutionMode = ExecutionMode.NORMAL,
    ) -> PlanLock:
        body = {
            "plan_id": plan_id,
            "interface_contract_hash": interface_contract_hash,
            "resolved_policies": resolved_policies,
            "module_hashes": module_hashes,
            "execution_mode": execution_mode.value,
        }
        ch = content_hash_of(body)
        return PlanLock(
            plan_id=plan_id,
            created_at=time.time(),
            interface_contract_hash=interface_contract_hash,
            resolved_policies=resolved_policies,
            module_hashes=module_hashes,
            execution_mode=execution_mode,
            content_hash=ch,
        )

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "interface_contract_hash": self.interface_contract_hash,
            "resolved_policies": self.resolved_policies,
            "module_hashes": self.module_hashes,
            "execution_mode": self.execution_mode.value,
            "content_hash": self.content_hash,
        }