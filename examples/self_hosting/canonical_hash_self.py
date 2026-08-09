"""
Self-hosting demo: Stage A (описание) + Stage C (исполнение графа + проверка).
"""
from __future__ import annotations

import json
from acid_engine.self_describe import build_self_contract
from acid_engine.self_hosting.stage_c import build_self_hosted_graph
from acid_engine.level2.conformance import check_conformance, explain_result
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level2.specification import Policy
from acid_engine.level2.serialization import content_hash_of
import time


def main():
    # Stage A: описание ядра
    iface = build_self_contract()
    print("=== Stage A: Self-Description ===")
    print(json.dumps(iface.to_canonical_dict(), indent=2, ensure_ascii=False))
    print(f"Interface contract hash: {iface.content_hash}")

    # Stage C: выполнение графа с проверкой конформности
    print("\n=== Stage C: Self-Hosted Execution with Conformance ===")
    pipeline = build_self_hosted_graph()
    test_data = {"z": 1, "a": [3, 2]}

    start = time.perf_counter()
    result = pipeline.execute(test_data)
    end = time.perf_counter()
    obs = ExecutionObservation.create(start=start, end=end, status="completed")

    expected_hash = content_hash_of(test_data)
    policy = Policy(pure=True, max_latency_ms=1000)
    result_check = check_conformance(
        required_output_type="str",
        provided_data=result,
        obs=obs,
        policy=policy,
        node_id="self_hosted_pipeline",
        contract_id="acid.self/core_pipeline",
        semantic_rules={"equals": expected_hash},
    )

    print(f"Output: {result}")
    print(f"Expected hash: {expected_hash}")
    print(explain_result(result_check))
    if result_check.ok:
        print("PASS (self-hosted graph conforms to its contract)")
    else:
        print("FAIL (self-hosted graph violated its contract)")


if __name__ == "__main__":
    main()