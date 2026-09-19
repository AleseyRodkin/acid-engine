"""Reusable Action and CLI name are on the product face."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_exposes_acid_judge_script():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'acid-judge = "acid_engine.cli:main"' in text
    assert 'name = "acid-judge"' in text
    assert 'name = "acid-engine"' not in text


def test_action_yml_runs_locks_index():
    text = (ROOT / "action.yml").read_text(encoding="utf-8")
    assert "using: composite" in text
    assert "acid-judge locks --index" in text
    assert "--judge" in text
    assert "proven_pure" not in text
    assert "MCP" not in text


def test_readme_install_has_no_pythonpath():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "acid-judge lock --script FILE" in readme
    assert "uses: AleseyRodkin/acid-engine@" in readme
    assert "uses: AleseyRodkin/acid-engine-2.0@" not in readme
    assert "judge: true" in readme
    assert "acid-judge-smoke" in readme
    assert "pip install" in readme
    assert "pip install acid-judge" in readme
    assert "Not published to PyPI" not in readme
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped.startswith("pip install"):
            assert "PYTHONPATH" not in line
            assert stripped != "pip install acid-engine"


def test_pypi_workflow_publishes_acid_judge_only():
    text = (ROOT / ".github" / "workflows" / "pypi.yml").read_text(encoding="utf-8")
    assert "acid_judge-" in text
    assert "dist_name: acid-engine" not in text
    assert 'name = "{name}"' not in text
