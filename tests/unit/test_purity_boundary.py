"""Epistemic boundary: Observed is not Proven for pure."""
from acid_engine.level2.conformance import check_conformance
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.python_runtime import run_script


def test_purity_is_not_proven_by_single_observation():
    """
    Checks that:
    - Observation has no proven_pure field
    - check_conformance does not infer that pure is proven
    on a single run without side effects.
    """
    def clean_func(x):
        return x + 1

    script = ScriptModule(
        contract_id=ContractId("test", "pure_test"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(pure=True)),
        input_type="int",
        output_type="int",
        implementation=clean_func,
        name="test_pure"
    )

    in_port = PortRef("test", "input", "val")
    snap = ContainerSnapshot.create(
        in_port, script.contract_id, script.content_hash, 1
    )
    out_snap, obs, delta, state = run_script(script, snap)

    # Observation has no proven_pure field
    assert not hasattr(obs, 'proven_pure'), \
        "Observation must not claim purity as proven"

    # effects_observed is empty, but that is not a proof
    assert obs.effects_observed == ()

    # check_conformance does not add proven_pure to the result
    result = check_conformance(
        required_output_type="int",
        provided_data=out_snap.data,
        obs=obs,
        policy=script.specification.policy,
    )
    # The message must not contain the word "proven"
    assert "proven" not in result.message.lower(), \
        f"Result message should not claim purity as proven, got: {result.message}"

    # The run itself succeeded (PASS)
    assert result.ok, f"Expected PASS, got {result.status}"

def test_purity_boundary_with_hidden_side_effect():
    """
    A function with a conditional side effect that does not fire
    on a normal input. The system must not treat pure as proven.
    """
    # Function with a dormant side effect
    def func_with_hidden_branch(x):
        if x > 1_000_000:          # will not fire for small x
            import requests  # potential network call
            requests.get("http://example.com")
        return x + 1

    script = ScriptModule(
        contract_id=ContractId("test", "hidden_effect"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(pure=True)),
        input_type="int",
        output_type="int",
        implementation=func_with_hidden_branch,
        name="hidden_branch_test"
    )

    in_port = PortRef("test", "input", "val")
    snap = ContainerSnapshot.create(
        in_port, script.contract_id, script.content_hash, 1
    )
    out_snap, obs, delta, state = run_script(script, snap)

    # Structural guarantee: Observation has no proven_pure field
    assert not hasattr(obs, 'proven_pure'), \
        "Observation must not claim purity as proven"

    # No effects observed in this run
    assert obs.effects_observed == ()

    # Conformance check must not contain "proven" in the message
    result = check_conformance(
        required_output_type="int",
        provided_data=out_snap.data,
        obs=obs,
        policy=script.specification.policy,
    )
    assert "proven" not in result.message.lower(), \
        f"Result message should not claim purity as proven, got: {result.message}"
    
    # The run succeeded (syntactically)
    assert result.ok