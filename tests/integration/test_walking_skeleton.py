import subprocess
import sys
from pathlib import Path


def test_walking_skeleton_script():
    """Run the walking skeleton as a script and check it exits with 0."""
    script_path = Path(__file__).parent.parent.parent / "examples" / "walking_skeleton" / "run_x_plus_1.py"
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert "PASS" in result.stdout