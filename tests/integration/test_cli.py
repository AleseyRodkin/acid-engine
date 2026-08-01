import subprocess
import sys
from pathlib import Path

def test_cli_no_args_runs_skeleton():
    """Без аргументов запускает walking skeleton."""
    result = subprocess.run(
        [sys.executable, "-m", "acid_engine"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "PASS" in result.stdout

def test_cli_with_script_file():
    """Запуск внешнего скрипта."""
    script_path = Path(__file__).parent.parent.parent / "examples" / "scaffold" / "script_template.py"
    result = subprocess.run(
        [sys.executable, "-m", "acid_engine", str(script_path), "5"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Output: 10" in result.stdout