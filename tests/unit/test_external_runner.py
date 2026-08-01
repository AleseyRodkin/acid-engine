import pytest
from acid_engine.execution.external_runner import run_external
from acid_engine.contracts.identity import ContractId
from acid_engine.execution.modes import ExecutionMode

def test_run_external_success():
    cid = ContractId("test", "echo")
    out, obs, delta, state = run_external(
        command=["echo", "hello"],
        contract_id=cid,
        contract_hash="hash",
        mode=ExecutionMode.LIGHT,
    )
    assert out.data["stdout"] == "hello"
    assert out.data["exit_code"] == 0
    assert obs.status == "completed"
    assert delta.status == "completed"

def test_run_external_failure():
    cid = ContractId("test", "fail")
    out, obs, delta, state = run_external(
        command=["bash", "-c", "exit 1"],
        contract_id=cid,
        contract_hash="hash",
        mode=ExecutionMode.LIGHT,
    )
    # external runner всегда возвращает output snapshot,
    # даже при неудаче, чтобы можно было проверить конформность
    assert out.data["exit_code"] == 1
    assert out.data["stdout"] == ""
    assert obs.status == "failed"
    assert state.status == "failed"

def test_run_external_timeout():
    cid = ContractId("test", "sleepy")
    out, obs, delta, state = run_external(
        command=["sleep", "2"],
        contract_id=cid,
        contract_hash="hash",
        timeout=0.1,
        mode=ExecutionMode.LIGHT,
    )
    assert obs.status == "failed"
    assert "timeout" in state.error_message

def test_run_external_with_stdin():
    cid = ContractId("test", "cat")
    out, obs, delta, state = run_external(
        command=["cat"],
        contract_id=cid,
        contract_hash="hash",
        stdin_data="hello stdin",
        mode=ExecutionMode.LIGHT,
    )
    assert out.data["stdout"] == "hello stdin"
    assert out.data["exit_code"] == 0