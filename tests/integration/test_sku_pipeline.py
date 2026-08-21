"""Второй реальный пайплайн (слой A): SKU normalize через честный контур."""
import os
import subprocess
import sys
from pathlib import Path

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.module.leaf import LeafModule

from examples.commerce.sku_normalize import (
    build_pipeline,
    build_clean_script,
    build_dedupe_script,
    run_leaf,
    make_plan,
)


def test_sku_pipeline_main():
    root = Path(__file__).parent.parent.parent
    script_path = root / "examples" / "commerce" / "sku_normalize.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(root),
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS" in result.stdout
    assert "plan.lock" in result.stdout


def test_sku_happy_path_gate():
    _, leaf_clean, leaf_dedupe = build_pipeline()
    data = ["  ab-01 ", "ab-01", "XY-9", 42, "", "  xy-9  ", None, "zz-3"]
    cleaned, obs1, conf1, _ = run_leaf(leaf_clean, data)
    assert conf1.ok
    assert obs1.status == "completed"
    assert cleaned == ["AB-01", "AB-01", "XY-9", "XY-9", "ZZ-3"]

    deduped, obs2, conf2, _ = run_leaf(leaf_dedupe, cleaned)
    assert conf2.ok
    assert deduped == ["AB-01", "XY-9", "ZZ-3"]


def test_agent_swap_dedupe_breaks_plan_lock():
    good = build_dedupe_script()
    bad = ScriptModule(
        contract_id=good.contract_id,
        version=good.version,
        specification=good.specification,
        input_type=good.input_type,
        output_type=good.output_type,
        implementation=lambda data: list(reversed(data)),
        name=good.name,
    )
    assert good.content_hash != bad.content_hash

    leaf_c = LeafModule("clean_node", build_clean_script())
    plan_good = make_plan(leaf_c, LeafModule("dedupe_node", good))
    plan_bad = make_plan(leaf_c, LeafModule("dedupe_node", bad))
    assert plan_good.content_hash != plan_bad.content_hash


def test_sku_type_fail():
    script = ScriptModule(
        contract_id=ContractId("commerce", "bad_sku"),
        version=Version(0, 1, 0),
        specification=Specification(policy=Policy(max_latency_ms=200)),
        input_type="list",
        output_type="list",
        implementation=lambda data: 12345,
        name="bad_sku",
    )
    leaf = LeafModule("bad", script)
    _, _, conf, _ = run_leaf(leaf, ["A"])
    assert not conf.ok
    assert conf.status == ConformanceStatus.FAIL
