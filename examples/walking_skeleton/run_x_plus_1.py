"""
Walking skeleton: Contract<int> → Snapshot → Script(x+1)
→ Observation → Provided ⊨ Required → PASS
+ InterfaceContract + PlanLock
"""
from __future__ import annotations

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.conformance import check_conformance, explain_result
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level2.specification import (
    Specification, Parameters, Policy, ImplementationRequirements,
)
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.python_runtime import run_script
from acid_engine.level2.resolver import ConstraintResolver
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.script.modes import ExecutionMode


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

    # Input snapshot
    in_port = PortRef(module="x_plus_1", direction="input", name="value")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=3,
        cardinality=1,
    )

    # Resolve constraints
    resolver = ConstraintResolver()
    effective_policy = resolver.resolve_policy(
        parent_policy={},
        child_policy=script.specification.policy.to_canonical_dict(),
    )

    # Execute
    output_snap, obs, delta, state = run_script(script, input_snap)

    # Conformance
    result = check_conformance(
        required_output_type="int",
        provided_data=output_snap.data,
        obs=obs,
        policy=script.specification.policy,
        node_id=script.name,
        contract_id=str(script.contract_id),
    )

    # Interface contract
    iface = InterfaceContract(
        contract_id=ContractId(namespace="demo", name="skeleton_iface"),
        version=Version(0, 1, 0),
        inputs={"value": "int"},
        outputs={"result": "int"},
        constraints=effective_policy,
        capabilities=["pure_transform"],
        module_hashes={leaf.module_id: leaf.content_hash},
    )

    # plan.lock
    plan = PlanLock.create(
        plan_id="skeleton-001",
        interface_contract_hash=iface.content_hash,
        resolved_policies=effective_policy,
        module_hashes=iface.module_hashes,
        execution_mode=ExecutionMode.NORMAL,
    )

    print("=== Walking Skeleton ===")
    print(f"input:  {input_snap.data}")
    print(f"output: {output_snap.data}")
    print(f"latency: {obs.latency_ms:.3f} ms")
    print(explain_result(result))
    print(f"plan.lock hash: {plan.content_hash[:16]}...")
    if result.failure:
        print(result.failure.human())

    assert result.ok, "Walking skeleton must PASS"
    assert output_snap.data == 4
    print("PASS")


if __name__ == "__main__":
    main()