import subprocess
import sys
from pathlib import Path

def test_self_hosting_stage():
    script_path = Path(__file__).parent.parent.parent / "examples" / "self_hosting" / "canonical_hash_self.py"
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    assert result.returncode == 0, f"Self-hosting demo failed: {result.stderr}"
    assert "PASS" in result.stdout