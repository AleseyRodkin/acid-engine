"""Тест эпистемической границы: Observed не равно Proven для pure."""
import pytest
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level3.script.python_runtime import run_script
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level2.conformance import check_conformance


def test_purity_is_not_proven_by_single_observation():
    """
    Проверяет, что:
    - Observation не содержит поля proven_pure
    - check_conformance не делает вывода о доказанности pure
    при единичном прогоне без side effects.
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

    # Observation не содержит поля proven_pure
    assert not hasattr(obs, 'proven_pure'), \
        "Observation must not claim purity as proven"

    # effects_observed пусты, но это не доказательство
    assert obs.effects_observed == ()

    # check_conformance не добавляет proven_pure в результат
    result = check_conformance(
        required_output_type="int",
        provided_data=out_snap.data,
        obs=obs,
        policy=script.specification.policy,
    )
    # Проверяем, что сообщение не содержит слова "proven"
    assert "proven" not in result.message.lower(), \
        f"Result message should not claim purity as proven, got: {result.message}"

    # Но сам прогон прошёл успешно (PASS)
    assert result.ok, f"Expected PASS, got {result.status}"