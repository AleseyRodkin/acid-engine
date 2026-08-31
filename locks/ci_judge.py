"""CI: judge every locks/index.json entry with --plan. Not a hosted registry."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "locks" / "index.json"
RECEIPTS = ROOT / "receipts"


def load_index(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SystemExit("locks/index.json has no entries")
    out: list[dict] = []
    for i, item in enumerate(entries):
        if not isinstance(item, dict):
            raise SystemExit(f"entry {i} is not an object")
        if not item.get("plan"):
            raise SystemExit(f"entry {item.get('id', i)}: plan required, will not judge")
        if not item.get("script"):
            raise SystemExit(f"entry {item.get('id', i)}: script required")
        out.append(item)
    return out


def judge_entry(entry: dict, receipts: Path) -> None:
    ident = str(entry.get("id") or Path(str(entry["script"])).stem)
    script = ROOT / str(entry["script"])
    plan = ROOT / str(entry["plan"])
    if not script.is_file():
        raise SystemExit(f"{ident}: script missing: {script}")
    if not plan.is_file():
        raise SystemExit(f"{ident}: plan missing: {plan}")
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = receipts / f"{ident}.json"
    cmd = [
        sys.executable,
        "-m",
        "acid_engine",
        "judge",
        "--script",
        str(script),
        "--plan",
        str(plan),
        "--input",
        json.dumps(entry.get("input")),
        "--receipt",
        str(receipt),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), env=env)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise SystemExit(f"{ident}: not PASS (exit {proc.returncode})")


def main() -> None:
    entries = load_index(INDEX)
    for entry in entries:
        judge_entry(entry, RECEIPTS)


if __name__ == "__main__":
    main()
