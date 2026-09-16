"""Top-level tool code must not run before source_hash matches the lock."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HONEST = '''
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.module import ScriptModule

def body(x):
    return x + 1

script = ScriptModule(
    contract_id=ContractId("t", "inc"),
    version=Version(0, 1, 0),
    specification=Specification(policy=Policy()),
    input_type="int",
    output_type="int",
    implementation=body,
    name="inc",
)
'''


def _cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-m", "acid_engine", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd),
    )


def test_import_time_side_effect_blocked_before_load(tmp_path: Path) -> None:
    tool = tmp_path / "inc.py"
    tool.write_text(HONEST, encoding="utf-8")
    plan = tmp_path / "inc.plan.json"
    lock = _cli("lock", "--script", str(tool), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    marker = tmp_path / "pwned"
    tool.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('pwn')\n" + HONEST,
        encoding="utf-8",
    )
    judged = _cli(
        "judge",
        "--script",
        str(tool),
        "--plan",
        str(plan),
        "--input",
        "1",
        cwd=tmp_path,
    )
    assert judged.returncode != 0
    assert "source_hash" in judged.stdout
    assert "was not imported" in judged.stdout
    assert not marker.exists()


def test_judge_without_plan_does_not_import(tmp_path: Path) -> None:
    marker = tmp_path / "pwned"
    tool = tmp_path / "inc.py"
    tool.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('pwn')\n" + HONEST,
        encoding="utf-8",
    )
    judged = _cli("judge", "--script", str(tool), "--input", "1", cwd=tmp_path)
    assert judged.returncode != 0
    assert "SKIPPED" in judged.stdout
    assert not marker.exists()


def test_honest_source_hash_still_passes(tmp_path: Path) -> None:
    tool = tmp_path / "inc.py"
    tool.write_text(HONEST, encoding="utf-8")
    plan = tmp_path / "inc.plan.json"
    lock = _cli("lock", "--script", str(tool), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    judged = _cli(
        "judge",
        "--script",
        str(tool),
        "--plan",
        str(plan),
        "--input",
        "1",
        cwd=tmp_path,
    )
    assert judged.returncode == 0, judged.stderr + judged.stdout
    assert "PASS" in judged.stdout


def test_missing_source_hash_is_skipped(tmp_path: Path) -> None:
    import json

    tool = tmp_path / "inc.py"
    tool.write_text(HONEST, encoding="utf-8")
    plan = tmp_path / "inc.plan.json"
    lock = _cli("lock", "--script", str(tool), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    payload = json.loads(plan.read_text(encoding="utf-8"))
    payload.pop("source_hash", None)
    plan.write_text(json.dumps(payload), encoding="utf-8")
    judged = _cli(
        "judge",
        "--script",
        str(tool),
        "--plan",
        str(plan),
        "--input",
        "1",
        cwd=tmp_path,
    )
    assert judged.returncode != 0
    assert "SKIPPED" in judged.stdout
    assert "source not pinned" in judged.stdout
    assert "PASS" not in judged.stdout


def test_load_execs_pinned_bytes_not_later_disk(tmp_path: Path) -> None:
    from acid_engine.cli import load_script_from_file
    from acid_engine.level2.local_deps import pin_source_bytes

    tool = tmp_path / "inc.py"
    tool.write_text(HONEST, encoding="utf-8")
    src = tool.read_bytes()
    pin_source_bytes(tool, src)
    tool.write_text(
        "raise SystemExit('pwned')\n" + HONEST,
        encoding="utf-8",
    )
    script = load_script_from_file(tool)
    assert script.implementation(1) == 2


def test_json_blank_side_effect_blocked_before_load(tmp_path: Path) -> None:
    """Judge the .json; side effect in implementation.file must not run on mismatch."""
    py = tmp_path / "inc.py"
    py.write_text(HONEST, encoding="utf-8")
    blank = tmp_path / "inc.json"
    blank.write_text(
        json.dumps(
            {
                "schema": "acid.blank.script.v1",
                "kind": "script",
                "contract_id": "t/inc",
                "version": "0.1.0",
                "name": "inc",
                "input_type": "int",
                "output_type": "int",
                "specification": {"policy": {}},
                "implementation": {
                    "language": "python",
                    "file": "inc.py",
                    "entry": "body",
                },
            }
        ),
        encoding="utf-8",
    )
    plan = tmp_path / "inc.plan.json"
    lock = _cli("lock", "--script", str(blank), "--out", str(plan), cwd=tmp_path)
    assert lock.returncode == 0, lock.stderr + lock.stdout
    marker = tmp_path / "pwned"
    py.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('pwn')\n" + HONEST,
        encoding="utf-8",
    )
    judged = _cli(
        "judge",
        "--script",
        str(blank),
        "--plan",
        str(plan),
        "--input",
        "1",
        cwd=tmp_path,
    )
    assert judged.returncode != 0
    assert "source_hash" in judged.stdout
    assert not marker.exists()

