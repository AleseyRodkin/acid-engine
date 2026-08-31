"""locks/index.json: пары script/plan/input. Подмена тела не PASS. CI не судит без plan."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from acid_engine.cli import load_script_from_file
from acid_engine.judge import judge_script
from acid_engine.level3.script.resolve import materialize_script
from acid_engine.level3.script.runner import load_script_lock
from locks.ci_judge import INDEX, load_index

ROOT = Path(__file__).resolve().parents[2]


def test_index_entries_have_plan_and_live_hash():
    entries = load_index(INDEX)
    assert entries
    for entry in entries:
        script_path = ROOT / str(entry["script"])
        plan_path = ROOT / str(entry["plan"])
        assert script_path.is_file(), entry
        assert plan_path.is_file(), entry
        script = materialize_script(load_script_from_file(script_path))
        plan_raw = json.loads(plan_path.read_text(encoding="utf-8"))
        locked = plan_raw["module_hashes"][script.name]
        assert locked == script.content_hash, entry["id"]


def test_index_bones_pass_and_swapped_plan_fails():
    entries = {e["id"]: e for e in load_index(INDEX)}
    bones = entries["n_plus_one"]
    script = materialize_script(load_script_from_file(ROOT / str(bones["script"])))
    raw = json.loads((ROOT / str(bones["plan"])).read_text(encoding="utf-8"))
    iface, plan = load_script_lock(raw)
    ok = judge_script(script, bones["input"], plan=plan, iface=iface)
    assert ok.ok
    raw["module_hashes"][script.name] = "0" * 64
    iface_bad, plan_bad = load_script_lock(raw)
    bad = judge_script(script, bones["input"], plan=plan_bad, iface=iface_bad)
    assert not bad.ok
    assert bad.failure is not None
    assert bad.failure.property_name == "module_hash"


def test_load_index_rejects_missing_plan():
    import tempfile

    from locks.ci_judge import load_index as load

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "index.json"
        p.write_text(
            json.dumps(
                {"schema": "acid.locks.v1", "entries": [{"id": "x", "script": "a.py"}]}
            ),
            encoding="utf-8",
        )
        try:
            load(p)
            assert False, "expected SystemExit"
        except SystemExit as e:
            assert "plan required" in str(e)


def test_ci_judge_script_never_calls_library_without_plan():
    text = (ROOT / "locks" / "ci_judge.py").read_text(encoding="utf-8")
    assert "judge_script" not in text
    yaml = (ROOT / ".github" / "workflows" / "acid-judge.yml").read_text(encoding="utf-8")
    assert "locks/ci_judge.py" in yaml
    assert "judge_script" not in yaml


def test_ci_judge_runs_index():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "locks" / "ci_judge.py")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS" in proc.stdout
    receipt = ROOT / "receipts" / "n_plus_one.json"
    assert receipt.is_file()
    rec = json.loads(receipt.read_text(encoding="utf-8"))
    assert rec["verdict"]["status"] == "PASS"
    assert "proven_pure" not in rec
