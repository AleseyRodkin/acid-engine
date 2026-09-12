"""Tutorial must not promise PASS without a lock."""
from pathlib import Path

TUTORIAL = Path(__file__).resolve().parents[2] / "TUTORIAL.md"
README = Path(__file__).resolve().parents[2] / "README.md"


def test_tutorial_does_not_teach_run_without_plan():
    text = TUTORIAL.read_text(encoding="utf-8")
    assert "run --script my_script.py --input 5" not in text
    assert "покажет PASS" not in text


def test_readme_does_not_point_at_tutorial():
    readme = README.read_text(encoding="utf-8")
    assert "TUTORIAL" not in readme
    assert "Tutorial.md" not in readme


def test_readme_does_not_revive_agent_slogan():
    readme = README.read_text(encoding="utf-8")
    assert "агент вызовет только" not in readme
    commercial = Path(__file__).resolve().parents[2] / "COMMERCIAL.md"
    assert "агент вызовет только" not in commercial.read_text(encoding="utf-8")


def test_readme_thirty_seconds():
    readme = README.read_text(encoding="utf-8")
    assert "ИИ может написать или изменить tool" in readme
    assert "SKIPPED, не PASS" in readme
    assert "does not have to believe it" in readme

