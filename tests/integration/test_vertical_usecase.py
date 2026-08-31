import os
import subprocess
import sys
from pathlib import Path


def test_vertical_usecase():
    script_path = (
        Path(__file__).parent.parent.parent
        / "examples"
        / "vertical_usecase"
        / "normalize_numbers.py"
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
    assert result.returncode == 0, f"Failed: {result.stderr}"
    assert "PASS" in result.stdout
