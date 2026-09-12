"""Reusable Action and CLI name are on the product face."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_exposes_acid_judge_script():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'acid-judge = "acid_engine.cli:main"' in text
    assert 'name = "acid-engine"' in text


def test_action_yml_runs_locks_index():
    text = (ROOT / "action.yml").read_text(encoding="utf-8")
    assert "using: composite" in text
    assert "acid-judge locks --index" in text
    assert "proven_pure" not in text
    assert "MCP" not in text


def test_readme_install_has_no_pythonpath():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "acid-judge lock --script FILE" in readme
    assert "uses: AleseyRodkin/acid-engine-2.0@" in readme
    assert "pip install" in readme
    for line in readme.splitlines():
        if line.startswith("acid-judge ") or line.startswith("pip install"):
            assert "PYTHONPATH" not in line
