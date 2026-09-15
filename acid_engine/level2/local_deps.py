"""Local project imports of a tool body. Not stdlib, not site-packages, not acid_engine."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

_STDLIB = frozenset(getattr(sys, "stdlib_module_names", ()))


def collect_local_dep_hashes(fn: Callable[..., Any] | None) -> dict[str, str]:
    """SHA-256 of local .py files the tool file imports. Empty if none or no source."""
    start = _origin_file(fn)
    if start is None:
        return {}
    root = start.parent
    out: dict[str, str] = {}
    _walk(start, root, out, set())
    return dict(sorted(out.items()))


def detect_dynamic_imports(fn: Callable[..., Any] | None) -> tuple[str, ...]:
    """Names in the tool file AST: import_module, __import__, exec, eval. Not pinned."""
    start = _origin_file(fn)
    if start is None:
        return ()
    try:
        tree = ast.parse(start.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return ()
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        qual = _call_qualname(node.func)
        tail = qual.rsplit(".", 1)[-1]
        if tail in {"exec", "eval", "__import__"}:
            found.add(tail)
        elif tail == "import_module":
            found.add("importlib.import_module")
    return tuple(sorted(found))


def _origin_file(fn: Callable[..., Any] | None) -> Path | None:
    if fn is None or not callable(fn):
        return None
    try:
        origin = inspect.getsourcefile(fn) or inspect.getfile(fn)
    except TypeError:
        return None
    if not origin or origin.startswith("<"):
        return None
    path = Path(origin).resolve()
    return path if path.is_file() else None


def _call_qualname(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        left = _call_qualname(func.value)
        return f"{left}.{func.attr}" if left else func.attr
    return ""


def _walk(file: Path, root: Path, out: dict[str, str], seen: set[Path]) -> None:
    file = file.resolve()
    if file in seen or not file.is_file():
        return
    seen.add(file)
    try:
        src = file.read_text(encoding="utf-8")
    except OSError:
        return
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        specs: list[tuple[str, int]] = []
        if isinstance(node, ast.Import):
            specs.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            specs.append((node.module or "", node.level))
        for mod, level in specs:
            resolved = _resolve(mod, level, file, root)
            if resolved is None:
                continue
            rel = _relkey(resolved, root)
            if rel not in out:
                out[rel] = hashlib.sha256(resolved.read_bytes()).hexdigest()
            _walk(resolved, root, out, seen)


def _relkey(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolve(mod: str, level: int, current: Path, root: Path) -> Path | None:
    head = mod.split(".", 1)[0] if mod else ""
    if level == 0 and head in _STDLIB:
        return None
    if level == 0 and head == "acid_engine":
        return None
    if level:
        base = current.parent
        for _ in range(max(level - 1, 0)):
            base = base.parent
        candidate = base.joinpath(*mod.split(".")) if mod else base
        return _py_file(candidate, root)
    if not mod:
        return None
    parts = mod.split(".")
    for base in (current.parent, root):
        found = _py_file(base.joinpath(*parts), root)
        if found is not None:
            return found
    try:
        spec = importlib.util.find_spec(mod)
    except (ImportError, ModuleNotFoundError, ValueError):
        return None
    origin = getattr(spec, "origin", None) if spec is not None else None
    if not origin or origin in {"built-in", "frozen"}:
        return None
    path = Path(origin).resolve()
    if path.suffix == ".py" and path.is_file() and _under(path, root):
        return path
    return None


def _py_file(candidate: Path, root: Path) -> Path | None:
    for path in (Path(str(candidate) + ".py"), candidate / "__init__.py"):
        if path.is_file() and _under(path, root):
            return path.resolve()
    return None


def seal_local_deps(fn: Callable[..., Any] | None) -> str | None:
    """Load pinned local deps from the bytes just hashed. None = sealed.

    Import after this sees the sealed module, not a later disk write.
    Returns the relative path that drifted, or None.
    """
    hashes = collect_local_dep_hashes(fn)
    if not hashes:
        return None
    start = _origin_file(fn)
    if start is None:
        return None
    return _seal_walk(start, start.parent, hashes, set(), is_root=True)


def _seal_walk(
    file: Path,
    root: Path,
    hashes: dict[str, str],
    seen: set[Path],
    *,
    is_root: bool,
) -> str | None:
    file = file.resolve()
    if file in seen or not file.is_file():
        return None
    seen.add(file)
    try:
        src = file.read_bytes()
        tree = ast.parse(src.decode("utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None
    for node in ast.walk(tree):
        specs: list[tuple[str, int]] = []
        if isinstance(node, ast.Import):
            specs.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            specs.append((node.module or "", node.level))
        for mod, level in specs:
            resolved = _resolve(mod, level, file, root)
            if resolved is None:
                continue
            err = _seal_walk(resolved, root, hashes, seen, is_root=False)
            if err is not None:
                return err
    if is_root:
        return None
    rel = _relkey(file, root)
    digest = hashes.get(rel)
    if digest is None:
        return None
    if hashlib.sha256(src).hexdigest() != digest:
        return rel
    name = rel[:-3].replace("/", ".") if rel.endswith(".py") else rel.replace("/", ".")
    module = types.ModuleType(name)
    module.__file__ = str(file)
    module.__package__ = name.rpartition(".")[0]
    sys.modules[name] = module
    exec(compile(src, str(file), "exec"), module.__dict__)  # noqa: S102
    return None
