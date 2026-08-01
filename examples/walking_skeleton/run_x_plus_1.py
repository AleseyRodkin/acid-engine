"""
Walking skeleton: Contract<int> → Snapshot → Script(x+1)
→ Observation → Provided ⊨ Required → PASS
"""
from __future__ import annotations

from acid_engine.contracts.identity import ContractId, Version
from acid_engine.contracts.conformance import check_conformance, explain_result
from acid_engine.containers.port import PortRef
from acid_engine.containers.snapshot import ContainerSnapshot
from acid_engine.scripts.specification import (
    Specification, Parameters, Policy, ImplementationRequirements,
)
from acid_engine.scripts.module import ScriptModule
from acid_engine.scripts.python_runtime import run_script


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

    in_port = PortRef(module="x_plus_1", direction="input", name="value")
    input_snap = ContainerSnapshot.create(
        port_ref=in_port,
        contract_id=script.contract_id,
        contract_hash=script.content_hash,
        data=3,
        cardinality=1,
    )

    resolver = ConstraintResolver()
    effective_policy = resolver.resolve_policy(
        parent_policy={},
        child_policy=script.specification.policy.to_canonical_dict(),
    )

    output_snap, obs, delta, state = run_script(script, input_snap)

    result = check_conformance(
        required_output_type="int",
        provided_data=output_snap.data,
        obs=obs,
        policy=script.specification.policy,
        node_id=script.name,
        contract_id=str(script.contract_id),
    )

    iface = InterfaceContract(
        contract_id=ContractId(namespace="demo", name="skeleton_iface"),
        version=Version(0, 1, 0),
        inputs={"value": "int"},
        outputs={"result": "int"},
        constraints=effective_policy,
        capabilities=["pure_transform"],
        module_hashes={leaf.module_id: leaf.content_hash},
    )

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