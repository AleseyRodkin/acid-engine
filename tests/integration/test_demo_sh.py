"""demo.sh: honest PASS then tamper blocked."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_demo_sh_blocks_tamper() -> None:
    proc = subprocess.run(
        ["bash", str(ROOT / "demo.sh")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        check=False,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "PASS" in proc.stdout
    assert "tamper blocked" in proc.stdout
    assert "demo failed" not in out
