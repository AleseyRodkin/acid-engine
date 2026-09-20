"""Local project imports of a tool body. Not stdlib, not site-packages, not acid_engine."""
from __future__ import annotations

import ast
import builtins
import contextvars
import hashlib
import importlib.util
import inspect
import sys
import threading
import types
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

_STDLIB = frozenset(getattr(sys, "stdlib_module_names", ()))
# Bytes hashed at the source_hash gate. Import/exec must use these, not a second read.
_PINNED_SOURCE: dict[str, bytes] = {}
# Per-judge sealed imports. Not a shared sys.modules["helper"] slot.
_SEALED: contextvars.ContextVar[dict[str, types.ModuleType] | None] = contextvars.ContextVar(
    "acid_sealed_imports", default=None
)
_ORIG_IMPORT: Any = None
_HOOK_LOCK = threading.Lock()


def pin_source_bytes(path: Path, src: bytes) -> None:
    """Remember the bytes that matched the lock. Later loads must exec these."""
    _PINNED_SOURCE[str(path.resolve())] = src


def read_source_bytes(path: Path) -> bytes:
    """Pinned snapshot if the gate already hashed this file, else a fresh disk read."""
    key = str(Path(path).resolve())
    pinned = _PINNED_SOURCE.get(key)
    if pinned is not None:
        return pinned
    return Path(path).read_bytes()


def snapshot_exec_target(path: Path) -> tuple[Path, bytes, str]:
    """One read of the presented file. JSON blanks: pin JSON + py; hash is py bytes."""
    presented = Path(path).resolve()
    if str(presented) not in _PINNED_SOURCE:
        pin_source_bytes(presented, presented.read_bytes())
    raw = read_source_bytes(presented)
    if presented.suffix.lower() != ".json":
        return presented, raw, hashlib.sha256(raw).hexdigest()
    target = _exec_target(presented)
    if target == presented:
        return presented, raw, hashlib.sha256(raw).hexdigest()
    if str(target) not in _PINNED_SOURCE:
        pin_source_bytes(target, target.read_bytes())
    src = read_source_bytes(target)
    return target, src, hashlib.sha256(src).hexdigest()


def exec_source_module(path: Path, src: bytes, mod_name: str) -> types.ModuleType:
    """Exec already-read bytes. Caller hashed these."""
    module = types.ModuleType(mod_name)
    resolved = str(Path(path).resolve())
    module.__file__ = resolved
    module.__package__ = ""
    sys.modules[mod_name] = module
    exec(compile(src, resolved, "exec"), module.__dict__)  # noqa: S102
    return module


def source_bytes_hash(path: Path) -> str:
    """SHA-256 of the file that would be exec'd. JSON blanks resolve to implementation.file."""
    return snapshot_exec_target(path)[2]


def origin_source_hash(fn: Callable[..., Any] | None) -> str | None:
    start = _origin_file(fn)
    if start is None:
        return None
    return hashlib.sha256(read_source_bytes(start)).hexdigest()


def _exec_target(path: Path) -> Path:
    path = path.resolve()
    if path.suffix.lower() != ".json":
        return path
    import json

    try:
        data = json.loads(read_source_bytes(path).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return path
    impl = data.get("implementation") if isinstance(data, dict) else None
    if not isinstance(impl, dict):
        return path
    rel = impl.get("file")
    if not rel:
        return path
    cand = Path(str(rel))
    if not cand.is_absolute():
        cand = path.parent / cand
    return cand.resolve() if cand.is_file() else path


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
        tree = ast.parse(read_source_bytes(start).decode("utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
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


def _import_specs(tree: ast.AST) -> list[tuple[str, int]]:
    """(module, level) from Import / ImportFrom, including from pkg import sub."""
    specs: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            specs.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            specs.append((node.module or "", node.level))
            for alias in node.names:
                if alias.name == "*":
                    continue
                if node.module:
                    specs.append((f"{node.module}.{alias.name}", node.level))
                else:
                    specs.append((alias.name, node.level))
    return specs


def _walk(file: Path, root: Path, out: dict[str, str], seen: set[Path]) -> None:
    file = file.resolve()
    if file in seen or not file.is_file():
        return
    seen.add(file)
    try:
        src = read_source_bytes(file).decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    for mod, level in _import_specs(tree):
        resolved = _resolve(mod, level, file, root)
        if resolved is None:
            continue
        rel = _relkey(resolved, root)
        if rel not in out:
            out[rel] = hashlib.sha256(read_source_bytes(resolved)).hexdigest()
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


def _import_name(rel: str) -> str:
    """Import name for a sealed file. Lock key stays the file path (dep:pkg/__init__.py)."""
    posix = rel.replace("\\", "/")
    if posix.endswith("/__init__.py"):
        return posix[: -len("/__init__.py")].replace("/", ".")
    if posix == "__init__.py":
        return ""
    if posix.endswith(".py"):
        posix = posix[:-3]
    return posix.replace("/", ".")


def _ensure_import_hook() -> None:
    """Install once. Consults the per-context sealed map; does not own sys.modules['helper']."""
    global _ORIG_IMPORT
    with _HOOK_LOCK:
        if _ORIG_IMPORT is not None:
            return
        _ORIG_IMPORT = builtins.__import__
        builtins.__import__ = cast(Any, _sealed_import)


def _calling_package(globals: dict[str, Any] | None) -> str | None:
    if not globals:
        return None
    package = globals.get("__package__")
    if isinstance(package, str) and package:
        return package
    spec = globals.get("__spec__")
    parent = getattr(spec, "parent", None) if spec is not None else None
    if isinstance(parent, str) and parent:
        return parent
    name = globals.get("__name__")
    if isinstance(name, str) and name and not name.startswith("acid_dep_"):
        return name.rpartition(".")[0] if "." in name else name
    return None


def _absolute_import_name(
    name: str,
    globals: dict[str, Any] | None,
    level: int,
) -> str | None:
    if level == 0:
        return name
    package = _calling_package(globals)
    if not package:
        return None
    rel = "." * level + (name or "")
    try:
        return importlib.util.resolve_name(rel, package)
    except (ImportError, ValueError):
        return None


def _sealed_import(
    name: str,
    globals: dict[str, Any] | None = None,
    locals: Any = None,
    fromlist: Any = (),
    level: int = 0,
) -> Any:
    orig = _ORIG_IMPORT
    sealed = _SEALED.get()
    if orig is None or not sealed:
        if orig is None:
            raise RuntimeError("import hook not installed")
        return orig(name, globals, locals, fromlist, level)
    abs_name = name
    if level:
        resolved = _absolute_import_name(name, globals, level)
        if resolved is None:
            return orig(name, globals, locals, fromlist, level)
        abs_name = resolved
    hit = sealed.get(abs_name)
    if hit is not None:
        if fromlist:
            return hit
        head = abs_name.split(".", 1)[0]
        return sealed.get(head, hit)
    return orig(name, globals, locals, fromlist, level)


def _acid_dep_prefix(mapping: dict[str, types.ModuleType]) -> str:
    return f"acid_dep_{id(mapping)}_"


def _pop_acid_dep(mapping: dict[str, types.ModuleType]) -> None:
    """Drop this seal's sys.modules keys. Never pop a bare helper name."""
    prefix = _acid_dep_prefix(mapping)
    for key in list(sys.modules):
        if key.startswith(prefix):
            sys.modules.pop(key, None)


def cleanup_sealed() -> None:
    """Worker finally: pop this context's acid_dep_* keys only."""
    mapping = _SEALED.get()
    if mapping:
        _pop_acid_dep(mapping)
    _SEALED.set(None)


def _attach_package(mapping: dict[str, types.ModuleType], name: str, module: types.ModuleType) -> None:
    if "." in name:
        parent_name, _, child = name.rpartition(".")
        parent = mapping.get(parent_name)
        if parent is not None:
            setattr(parent, child, module)
    prefix = name + "."
    for child_name, child_mod in list(mapping.items()):
        if child_name.startswith(prefix) and "." not in child_name[len(prefix) :]:
            setattr(module, child_name[len(prefix) :], child_mod)


def _seal_enter(
    fn: Callable[..., Any] | None,
    locked: dict[str, str] | None,
) -> tuple[str | None, Any, dict[str, types.ModuleType] | None]:
    """Discover + verify all hashes, then placeholders, then exec pinned bytes."""
    start = _origin_file(fn)
    if start is None:
        return None, None, None
    root = start.parent
    discovered: dict[Path, bytes] = {}
    _discover(start, root, discovered, set())
    deps = [(path, src) for path, src in discovered.items() if path != start]
    if locked is not None:
        hashes = dict(locked)
    else:
        hashes = {
            _relkey(path, root): hashlib.sha256(src).hexdigest() for path, src in deps
        }
        if not hashes:
            return None, None, None
    sealed: set[str] = set()
    prepared: list[tuple[Path, bytes, str, str]] = []
    for path, src in deps:
        rel = _relkey(path, root)
        digest = hashes.get(rel)
        if digest is None or hashlib.sha256(src).hexdigest() != digest:
            return rel, None, None
        sealed.add(rel)
        prepared.append((path, src, rel, _import_name(rel)))
    missing = sorted(set(hashes) - sealed)
    if missing:
        return missing[0], None, None
    _ensure_import_hook()
    mapping: dict[str, types.ModuleType] = {}
    token = _SEALED.set(mapping)
    for path, _src, _rel, name in prepared:
        module = types.ModuleType(name)
        module.__file__ = str(path)
        if path.name == "__init__.py":
            module.__package__ = name
            module.__path__ = [str(path.parent)]
        else:
            module.__package__ = name.rpartition(".")[0]
        sys.modules[f"{_acid_dep_prefix(mapping)}{name}"] = module
        mapping[name] = module
    for _path, _src, _rel, name in prepared:
        _attach_package(mapping, name, mapping[name])
    try:
        for path, src, _rel, name in prepared:
            exec(compile(src, str(path), "exec"), mapping[name].__dict__)  # noqa: S102
    except Exception:
        _SEALED.reset(token)
        _pop_acid_dep(mapping)
        raise
    return None, token, mapping


def _discover(
    file: Path,
    root: Path,
    out: dict[Path, bytes],
    seen: set[Path],
) -> None:
    file = file.resolve()
    if file in seen or not file.is_file():
        return
    seen.add(file)
    try:
        src = read_source_bytes(file)
        tree = ast.parse(src.decode("utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return
    for mod, level in _import_specs(tree):
        resolved = _resolve(mod, level, file, root)
        if resolved is None:
            continue
        _discover(resolved, root, out, seen)
    out[file] = src


def seal_local_deps(
    fn: Callable[..., Any] | None,
    locked: dict[str, str] | None = None,
) -> str | None:
    """Load local deps from one read of each file. Compare to locked hashes, not a second scan.

    Import after this sees the sealed module, not a later disk write.
    Returns the relative path that drifted, or None.
    locked=None: hash the tree as it is now (lock / tests).
    locked={}: still walk; an undeclared local import is FAIL.
    Does not reset on success: reset before execute would unseal. Execute paths use sealed_deps.
    """
    leaked, _token, _mapping = _seal_enter(fn, locked)
    return leaked


@contextmanager
def sealed_deps(
    fn: Callable[..., Any] | None,
    locked: dict[str, str] | None = None,
) -> Iterator[str | None]:
    """Seal for the with-block, then pop this mapping's acid_dep_* keys."""
    leaked, token, mapping = _seal_enter(fn, locked)
    try:
        yield leaked
    finally:
        if token is not None:
            _SEALED.reset(token)
        if mapping is not None:
            _pop_acid_dep(mapping)


