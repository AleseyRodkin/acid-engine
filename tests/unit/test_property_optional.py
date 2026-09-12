"""Property tests must collect when hypothesis is absent."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_property_module_uses_importorskip():
    text = (ROOT / "tests" / "property" / "test_resolver_properties.py").read_text(
        encoding="utf-8"
    )
    assert "importorskip" in text
    assert text.index("importorskip") < text.index("from hypothesis")
