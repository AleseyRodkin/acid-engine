"""Canonical fingerprint of a Python callable for identity hashing.

Canon: AST of source when it can be parsed; otherwise bytecode.
Closure cells and defaults are always included — they are part of what runs.
"""
from __future__ import annotations

import ast
import functools
import inspect
import textwrap
from collections.abc import Callable, Iterator
from types import CodeType
from typing import Any


def canonical_implementation(
    fn: Callable[..., Any],
    *,
    _seen: set[int] | None = None,
) -> dict[str, Any]:
    """Stable, JSON-safe fingerprint of the callable that will actually run."""
    seen = set(_seen or ())
    marker = id(fn)
    if marker in seen:
        return {"kind": "cycle"}
    seen.add(marker)

    if isinstance(fn, functools.partial):
        return {
            "kind": "partial",
            "func": canonical_implementation(fn.func, _seen=seen),
            "args": [_jsonable(a, seen) for a in fn.args],
            "keywords": {
                str(k): _jsonable(v, seen)
                for k, v in sorted((fn.keywords or {}).items())
            },
        }

    body = _callable_body(fn)
    return {
        "kind": body["kind"],
        "body": body["body"],
        "closure": _closure_canon(fn, seen),
        "defaults": _jsonable(getattr(fn, "__defaults__", None) or (), seen),
        "kwdefaults": _jsonable(getattr(fn, "__kwdefaults__", None) or {}, seen),
    }


def _callable_body(fn: Callable[..., Any]) -> dict[str, Any]:
    dump = _ast_dump(fn)
    if dump is not None:
        return {"kind": "ast", "body": dump}
    code = getattr(fn, "__code__", None)
    if isinstance(code, CodeType):
        return {"kind": "bytecode", "body": _code_canon(code)}
    return {
        "kind": "opaque",
        "body": {
            "module": getattr(fn, "__module__", "") or "",
            "qualname": getattr(fn, "__qualname__", "") or "",
            "repr": repr(fn),
        },
    }


def _ast_dump(fn: Callable[..., Any]) -> str | None:
    try:
        raw = inspect.getsource(fn)
    except (OSError, TypeError):
        return None
    tree = _parse_source(raw)
    if tree is None:
        return None
    node = _first_callable_node(tree)
    if node is None:
        return None
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node.name = "_"
    # unparse, не ast.dump: поля узла растут с версией CPython (3.12 type_params).
    return ast.unparse(node)


def _parse_source(raw: str) -> ast.AST | None:
    src = textwrap.dedent(raw).strip().rstrip(",")
    for candidate in _source_candidates(src):
        try:
            parsed: ast.AST = ast.parse(candidate)
            return parsed
        except SyntaxError:
            continue
    return None


def _source_candidates(src: str) -> Iterator[str]:
    yield src
    yield f"_ = {src}"
    if "=" in src:
        _, right = src.split("=", 1)
        rhs = right.strip().rstrip(",")
        yield rhs
        yield f"_ = {rhs}"


def _first_callable_node(tree: ast.AST) -> ast.AST | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    return None


def _closure_canon(fn: Callable[..., Any], seen: set[int]) -> list[dict[str, Any]]:
    closure = getattr(fn, "__closure__", None)
    code = getattr(fn, "__code__", None)
    if not closure or not isinstance(code, CodeType):
        return []
    out: list[dict[str, Any]] = []
    for name, cell in zip(code.co_freevars, closure):
        try:
            value = cell.cell_contents
        except ValueError:
            out.append({"name": name, "value": {"kind": "empty_cell"}})
            continue
        out.append({"name": name, "value": _jsonable(value, seen)})
    return out


def _code_canon(code: CodeType) -> dict[str, Any]:
    return {
        "co_code": code.co_code.hex(),
        "co_consts": [_const_canon(c) for c in code.co_consts],
        "co_names": list(code.co_names),
        "co_varnames": list(code.co_varnames),
        "co_freevars": list(code.co_freevars),
        "co_cellvars": list(code.co_cellvars),
    }


def _const_canon(value: Any) -> Any:
    if isinstance(value, CodeType):
        return {"kind": "code", "code": _code_canon(value)}
    if isinstance(value, bytes):
        return {"kind": "bytes", "hex": value.hex()}
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    if isinstance(value, tuple):
        return [_const_canon(v) for v in value]
    if isinstance(value, type):
        return {
            "kind": "type",
            "qualname": f"{value.__module__}.{value.__qualname__}",
        }
    return {"kind": "repr", "type": type(value).__name__, "repr": repr(value)}


def implementation_identity(fn: Callable[..., Any] | None) -> Any:
    """Канон тела для identity. Нет callable — missing. Ссылка сюда не входит."""
    if fn is None:
        return {"kind": "missing"}
    return canonical_implementation(fn)


def _jsonable(value: Any, seen: set[int]) -> Any:
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    if isinstance(value, bytes):
        return {"kind": "bytes", "hex": value.hex()}
    if isinstance(value, dict):
        return {str(k): _jsonable(value[k], seen) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v, seen) for v in value]
    if callable(value):
        return canonical_implementation(value, _seen=seen)
    return {"kind": "repr", "type": type(value).__name__, "repr": repr(value)}
