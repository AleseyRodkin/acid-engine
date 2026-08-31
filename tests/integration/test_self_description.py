import os
import subprocess
import sys
from pathlib import Path


def test_self_description_runs():
    script_path = (
        Path(__file__).parent.parent.parent / "examples" / "self_description" / "describe.py"
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        env=env,
        cwd="/tmp",
    )
    assert result.returncode == 0, f"Self-description failed: {result.stderr}"
    assert "Interface contract hash:" in result.stdout
    assert "0000000" not in result.stdout
