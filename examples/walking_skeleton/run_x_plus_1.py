"""Walking skeleton: Script(x+1) через judge_script / plan.lock."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acid_engine.judge import judge_script
from acid_engine.level2.conformance import explain_result
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.resolver import ConstraintResolver
from acid_engine.level2.specification import (
    ImplementationRequirements,
    Parameters,
    Policy,
    Specification,
)
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level3.script.module import ScriptModule


def build_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId(namespace="demo", name="x_plus_1"),
        version=Version(0, 1, 0),
        specification=Specification(
            parameters=Parameters(values={}),
            policy=Policy(pure=True, max_latency_ms=100.0),
            implementation_requirements=ImplementationRequirements(),
        ),
        input_type="int",
        output_type="int",
        implementation=lambda x: x + 1,
        name="x_plus_1",
    )


def main() -> None:
    script = build_script()
    leaf = LeafModule(module_id="leaf_x_plus_1", script=script)

    resolver = ConstraintResolver()
    effective_policy = resolver.resolve_policy(
        parent_policy={},
        child_policy=script.specification.policy.to_canonical_dict(),
    )

    iface = InterfaceContract(
        contract_id=ContractId(namespace="demo", name="skeleton_iface"),
        version=Version(0, 1, 0),
        inputs={"value": "int"},
        outputs={"result": "int"},
        constraints=effective_policy,
        capabilities=["pure_transform"],
        module_hashes={script.name: script.content_hash},
    )
    plan = PlanLock.create(
        plan_id="skeleton-001",
        interface_contract_hash=iface.content_hash,
        resolved_policies=effective_policy,
        module_hashes=iface.module_hashes,
        execution_mode=ExecutionMode.NORMAL,
    )

    result = judge_script(script, 3, plan=plan, iface=iface)

    print("=== Walking Skeleton ===")
    print("input:  3")
    print(f"output: {result.data}")
    print(explain_result(result.conformance))
    print(f"plan.lock hash: {plan.content_hash[:16]}...")
    assert result.ok, "Walking skeleton must PASS"
    assert result.data == 4
    assert leaf.content_hash == script.content_hash
    print("PASS")


if __name__ == "__main__":
    main()
