import subprocess
import sys
from pathlib import Path


def test_self_description_runs():
    script_path = Path(__file__).parent.parent.parent / "examples" / "self_description" / "describe.py"
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    assert result.returncode == 0, f"Self-description failed: {result.stderr}"
    assert "Interface contract hash:" in result.stdout
    # Хеш должен быть ненулевым
    assert "0000000" not in result.stdout  # простой признак, что хеш не пустой