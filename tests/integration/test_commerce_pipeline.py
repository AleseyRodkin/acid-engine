"""First real pipeline (layer A): order amounts through the honest contour."""
import subprocess
import sys
from pathlib import Path

from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.runner import execute_plan
from acid_engine.worker import live_toolchain
from examples.commerce.order_amounts import (
    build_filter_script,
    build_pipeline,
    build_scale_script,
    lock_pair,
    make_plan,
    run_leaf,
)


def test_commerce_pipeline_main():
    script_path = (
        Path(__file__).parent.parent.parent
        / "examples"
        / "commerce"
        / "order_amounts.py"
    )
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(script_path.parent.parent.parent)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(script_path.parent.parent.parent),
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS" in result.stdout
    assert "plan.lock" in result.stdout


def test_commerce_happy_path_gate():
    _, leaf_filter, leaf_scale = build_pipeline()
    data = [15000, -200, 0, True, 25050, 100]
    filtered, obs1, conf1, _ = run_leaf(leaf_filter, data)
    assert conf1.ok
    assert obs1.status == "completed"
    assert filtered == [15000, 0, 25050, 100]

    scaled, obs2, conf2, _ = run_leaf(leaf_scale, filtered)
    assert conf2.ok
    assert scaled == [150.0, 0.0, 250.5, 1.0]


def test_agent_swap_impl_breaks_plan_lock():
    """Swapping the scale body with the same declaration changes the hash and plan.lock."""
    good = build_scale_script()
    bad = ScriptModule(
        contract_id=good.contract_id,
        version=good.version,
        specification=good.specification,
        input_type=good.input_type,
        output_type=good.output_type,
        implementation=lambda data: [x / 50 for x in data],  # different implementation
        name=good.name,
    )
    assert good.content_hash != bad.content_hash

    leaf_f = LeafModule("filter_node", build_filter_script())
    plan_good = make_plan(leaf_f, LeafModule("scale_node", good))
    plan_bad = make_plan(leaf_f, LeafModule("scale_node", bad))
    assert plan_good.content_hash != plan_bad.content_hash


def test_commerce_type_fail():
    """Wrong output type → FAIL, not PASS."""
    script = ScriptModule(
        contract_id=ContractId("commerce", "bad"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(max_latency_ms=200)),
        input_type="list",
        output_type="list",
        implementation=lambda data: "not-a-list",
        name="bad",
    )
    leaf = LeafModule("bad", script)
    _, _, conf, _ = run_leaf(leaf, [1, 2, 3])
    assert not conf.ok
    assert conf.status == ConformanceStatus.FAIL


def test_orders_via_execute_plan():
    _, leaf_f, leaf_s = build_pipeline()
    iface, plan = lock_pair(leaf_f, leaf_s)
    step1 = execute_plan(iface, plan, leaf_f.script, [15000, -200, True, 100], toolchain=live_toolchain())
    assert step1.ok
    assert step1.data == [15000, 100]
    step2 = execute_plan(iface, plan, leaf_s.script, step1.data, toolchain=live_toolchain())
    assert step2.ok
    assert step2.data == [150.0, 1.0]
