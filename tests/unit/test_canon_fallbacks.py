"""Fallback branches of implementation_canon: candidates, consts, kinds."""
from __future__ import annotations

import ast

from acid_engine.level2.implementation_canon import (
    _const_canon,
    _source_candidates,
    canon_id_for,
    canonical_implementation,
    live_canon_kind,
)


def test_source_candidates_covers_assignment_and_wrapper():
    src = "f = lambda x: x + 1"
    cands = list(_source_candidates(src))
    assert src in cands
    assert any(c.startswith("_ = ") for c in cands)
    parsed = 0
    for c in cands:
        try:
            ast.parse(c)
            parsed += 1
        except SyntaxError:
            continue
    assert parsed >= 1


def test_const_canon_bytes_type_tuple_and_repr():
    assert _const_canon(b"ab") == {"kind": "bytes", "hex": "6162"}
    assert _const_canon(int)["kind"] == "type"
    assert _const_canon((1, b"x"))[1]["kind"] == "bytes"

    class Weird:
        def __repr__(self) -> str:
            return "Weird()"

    blob = _const_canon(Weird())
    assert blob["kind"] == "repr"
    assert blob["type"] == "Weird"


def test_live_canon_kind_ast_and_missing():
    def add(x: int) -> int:
        return x + 1

    assert live_canon_kind(add) == "ast"
    assert live_canon_kind(None) == "missing"
    ident = canonical_implementation(add)
    assert ident["kind"] == "ast"
    assert canon_id_for("ast") == "python.ast.v1"
    assert canon_id_for("nope") == "python.nope.v1"
