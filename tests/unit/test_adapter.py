from acid_engine.level3.orchestration.adapter import LocalAdapter
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level2.conformance import ConformanceStatus


def test_local_adapter():
    adapter = LocalAdapter()
    plan = PlanLock.create(
        plan_id="test-plan",
        interface_contract_hash="hash",
        resolved_policies={},
        module_hashes={},
        execution_mode=ExecutionMode.NORMAL,
    )
    run_id = adapter.submit_plan(plan)
    assert run_id == "local-test-plan"
    assert adapter.get_status(run_id) == "not_executed"
    result = adapter.get_result(run_id)
    assert result is not None
    assert not result.ok
    assert result.status == ConformanceStatus.SKIPPED
