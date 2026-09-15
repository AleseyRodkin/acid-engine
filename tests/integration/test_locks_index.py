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
from acid_engine.worker import RUNTIME_PIN_PATHS, runtime_hashes, source_hash
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
        assert plan_raw["toolchain"]["worker_hash"] == source_hash()
        assert plan_raw["toolchain"]["runtime_hashes"] == runtime_hashes()


def test_index_pins_live_worker():
    raw = json.loads(INDEX.read_text(encoding="utf-8"))
    assert raw["worker_hash"] == source_hash()
    assert raw["runtime_hashes"] == runtime_hashes()
    assert set(raw["runtime_hashes"]) == set(RUNTIME_PIN_PATHS)


def test_index_bones_pass_and_swapped_plan_fails():
    entries = {e["id"]: e for e in load_index(INDEX)}
    bones = entries["n_plus_one"]
    script = materialize_script(load_script_from_file(ROOT / str(bones["script"])))
    raw = json.loads((ROOT / str(bones["plan"])).read_text(encoding="utf-8"))
    iface, plan = load_script_lock(raw)
    ok = judge_script(script, bones["input"], plan=plan, iface=iface, toolchain=raw)
    assert ok.ok
    raw["module_hashes"][script.name] = "0" * 64
    iface_bad, plan_bad = load_script_lock(raw)
    bad = judge_script(
        script, bones["input"], plan=plan_bad, iface=iface_bad, toolchain=raw
    )
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


def test_locks_index_missing_worker_hash_is_fail(tmp_path: Path):
    idx = tmp_path / "index.json"
    idx.write_text(
        json.dumps(
            {
                "schema": "acid.locks.v1",
                "entries": [
                    {
                        "id": "n_plus_one",
                        "script": "examples/bones/n_plus_one.json",
                        "plan": "examples/bones/n_plus_one.plan.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, "-m", "acid_engine", "locks", "--index", str(idx)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
    )
    assert proc.returncode != 0
    assert "worker_hash missing" in proc.stdout


def test_ci_judge_requires_runtime_pin():
    from locks.ci_judge import require_runtime_pin

    try:
        require_runtime_pin({"schema": "acid.locks.v1", "entries": []})
        assert False, "expected SystemExit"
    except SystemExit as e:
        assert "worker_hash required" in str(e)


def test_ci_judge_script_never_calls_library_without_plan():
    text = (ROOT / "locks" / "ci_judge.py").read_text(encoding="utf-8")
    assert "judge_script" not in text
    yaml = (ROOT / ".github" / "workflows" / "acid-judge.yml").read_text(encoding="utf-8")
    assert "judge: true" in yaml
    assert "judge_script" not in yaml
    assert "pytest" in yaml
    assert "ruff check" in yaml
    assert "mypy --strict" in yaml
    assert "cargo test" in yaml
    assert "3.11" in yaml
    assert "3.12" in yaml


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
