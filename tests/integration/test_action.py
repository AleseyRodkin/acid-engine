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


def test_action_verify_run_has_no_input_interpolation():
    text = (ROOT / "action.yml").read_text(encoding="utf-8")
    start = text.index("name: Verify lock index")
    end = text.index("name: Upload receipts")
    run = text[start:end].split("run:", 1)[1]
    assert "${{ inputs." not in run
    assert "ACID_INDEX: ${{ inputs.index }}" in text
    assert "ACID_JUDGE: ${{ inputs.judge }}" in text
    assert "ACID_RECEIPTS: ${{ inputs.receipts }}" in text


def test_action_fetches_supervisor_from_release_tag():
    text = (ROOT / "action.yml").read_text(encoding="utf-8")
    assert "name: Fetch supervisor" in text
    fetch = text.split("name: Fetch supervisor", 1)[1].split("name: Verify lock index", 1)[0]
    assert "github.action_ref" in fetch or "ACID_ACTION_REF" in fetch
    assert "acid-judge-linux-x86_64" in fetch
    assert "releases/download/" in fetch
    assert "${{ inputs." not in fetch
    assert "@main" not in fetch
    assert "v0.2." in fetch
    verify = text.split("name: Verify lock index", 1)[1].split("name: Upload receipts", 1)[0]
    assert "path=supervisor" in verify
    assert "path=python-cli" in verify
    assert "acid-judge locks --index" in verify
    assert "python -m acid_engine.action_driver" in verify
    assert "for i, item in enumerate(entries)" not in text
    assert "${{ inputs." not in verify.split("run:", 1)[1]


def test_action_fetch_checks_release_checksum():
    text = (ROOT / "action.yml").read_text(encoding="utf-8")
    fetch = text.split("name: Fetch supervisor", 1)[1].split("name: Verify lock index", 1)[0]
    assert "acid-judge-linux-x86_64.sha256" in fetch
    assert "sha256sum -c" in fetch
    assert "checksum mismatch" in fetch
    assert "${{ inputs." not in fetch
    assert "releases/download/" in fetch


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
