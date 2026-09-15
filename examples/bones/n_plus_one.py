"""Bone: dict {n: 3} → {n: 4}. One step through execute_plan."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acid_engine.judge import judge_script_from_lock
from acid_engine.level2.conformance import explain_result
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule


def bump_n(data: dict) -> dict:
    if type(data) is not dict:
        raise TypeError("expected dict")
    n = data.get("n")
    if type(n) is not int:
        raise TypeError("n must be int")
    out = dict(data)
    out["n"] = n + 1
    return out


def build_script() -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("bones", "n_plus_one"),
        version=Version(0, 1, 0),
        specification=Specification(
            policy=Policy(pure=True, max_latency_ms=200.0),
        ),
        input_type="dict",
        output_type="dict",
        implementation=bump_n,
        name="n_plus_one",
    )


def main() -> None:
    script = build_script()
    incoming = {"n": 3}
    plan_path = Path(__file__).with_name("n_plus_one.plan.json")
    result = judge_script_from_lock(script, incoming, plan_path)

    expected = {"n": 4}
    print("=== bones: n_plus_one ===")
    print(f"input:    {incoming}")
    print(f"output:   {result.data}")
    print(f"expected: {expected}")
    print(explain_result(result.conformance))
    print(f"plan.lock: {plan_path.name}")
    assert result.ok, explain_result(result.conformance)
    assert result.data == expected
    assert not hasattr(result.observation, "proven_pure")
    print("PASS")


if __name__ == "__main__":
    main()
