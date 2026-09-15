"""Tutorial must not promise PASS without a lock."""
from pathlib import Path

TUTORIAL = Path(__file__).resolve().parents[2] / "TUTORIAL.md"
README = Path(__file__).resolve().parents[2] / "README.md"


def test_tutorial_does_not_teach_run_without_plan():
    text = TUTORIAL.read_text(encoding="utf-8")
    assert "run --script my_script.py --input 5" not in text
    assert "will show PASS" not in text


def test_readme_does_not_point_at_tutorial():
    readme = README.read_text(encoding="utf-8")
    assert "TUTORIAL" not in readme
    assert "Tutorial.md" not in readme


def test_readme_does_not_revive_agent_slogan():
    readme = README.read_text(encoding="utf-8")
    assert "the agent will only call" not in readme
    commercial = Path(__file__).resolve().parents[2] / "COMMERCIAL.md"
    assert "the agent will only call" not in commercial.read_text(encoding="utf-8")


def test_readme_thirty_seconds():
    readme = README.read_text(encoding="utf-8")
    assert "An agent can write or change a tool" in readme
    assert "SKIPPED is not PASS" in readme
    assert "does not have to believe it" in readme
    assert "Trust continuity" in readme
    assert "trust layer" in readme
    assert "Verify what your AI agent actually executes" in readme
    assert "approved artifact" in readme
    assert "Approved-to-executed" in readme
    assert "We don't tell you that your code is safe" in readme
    assert "SKIPPED is not PASS" in readme
    assert "attacks/" in readme
    assert "TRUST.md" in readme
    assert "Before execution" in readme
    assert "After execution" in readme
    assert "./demo.sh" in readme
    assert "Pre ≠ PASS" in readme
    assert "Python-first" in readme
    assert "INTEROP.md" in readme
    assert "execution-integrity layer" in readme
    assert "Verify it yourself" in readme
    assert "acid-judge-smoke" in readme
    assert "./smoke.sh" in readme

