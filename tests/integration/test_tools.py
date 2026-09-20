"""Five locked tools: live hash == plan, swap FAIL, expected outputs."""
from __future__ import annotations

import json
from pathlib import Path

from acid_engine.cli import load_script_from_file
from acid_engine.judge import judge_script
from acid_engine.level3.script.resolve import materialize_script
from acid_engine.level3.script.runner import load_script_lock
from examples.tools.clean_text import clean_text
from examples.tools.compute_amount import compute_amount
from examples.tools.emit_forecast_card import emit_forecast_card
from examples.tools.normalize_id import normalize_id
from examples.tools.route_ticket import route_ticket

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "examples" / "tools"

CASES = [
    ("clean_text", {"text": "  Hello   WORLD "}, {"text": "hello world"}),
    ("normalize_id", {"id": " sku-12a "}, {"id": "SKU-12A"}),
    ("compute_amount", {"cents": 1999, "qty": 2}, {"cents": 3998}),
    ("route_ticket", {"queue": "billing"}, {"queue": "billing"}),
    ("emit_forecast_card", {"title": "alpha", "items": ["a", "b"]}, {"title": "alpha", "count": 2}),
]


def _load(name: str):
    script = materialize_script(load_script_from_file(TOOLS / f"{name}.json"))
    raw = json.loads((TOOLS / f"{name}.plan.json").read_text(encoding="utf-8"))
    iface, plan = load_script_lock(raw)
    return script, iface, plan


def test_tools_unit_outputs():
    assert clean_text({"text": "  Hello   WORLD "}) == {"text": "hello world"}
    assert normalize_id({"id": " sku-12a "}) == {"id": "SKU-12A"}
    assert compute_amount({"cents": 1999, "qty": 2}) == {"cents": 3998}
    assert route_ticket({"queue": "billing"}) == {"queue": "billing"}
    assert emit_forecast_card({"title": "alpha", "items": ["a", "b"]}) == {
        "title": "alpha",
        "count": 2,
    }


def test_tools_bool_is_not_int_and_unknown_queue():
    try:
        compute_amount({"cents": True, "qty": 1})
        assert False
    except TypeError:
        pass
    try:
        route_ticket({"queue": "invented"})
        assert False
    except ValueError:
        pass


def test_tools_locked_pass_and_swap_fails():
    for name, incoming, expected in CASES:
        script, iface, plan = _load(name)
        raw = json.loads((TOOLS / f"{name}.plan.json").read_text(encoding="utf-8"))
        assert plan.module_hashes[name] == script.content_hash
        result = judge_script(script, incoming, plan=plan, iface=iface, toolchain=raw)
        assert result.ok, (name, result.conformance.message)
        assert result.data == expected
        raw["module_hashes"][name] = "0" * 64
        raw.pop("plan_content_hash", None)
        iface_bad, plan_bad = load_script_lock(raw)
        bad = judge_script(
            script, incoming, plan=plan_bad, iface=iface_bad, toolchain=raw
        )
        assert not bad.ok
        assert bad.failure is not None
        assert bad.failure.property_name == "module_hash"
