# Security

Report a vulnerability privately: open a GitHub Security Advisory on
[AleseyRodkin/acid-engine-2.0](https://github.com/AleseyRodkin/acid-engine-2.0)
or email the account that owns that repository. Target response: 7 days.

This is a fail-closed **file lock** on a locally approved Python-tool body
(and its local `.py` imports, and the judge contour). It is not a sandbox
and not an MCP gateway.

## In perimeter

- Bytes of the locked tool file **before import** (`source_hash`). A
  top-level side effect in the file cannot run until this matches.
  CLI `judge`/`locks`/`diff`, the supervisor worker, and the Claude Code
  hook all apply this gate. `lock` loads the file you present (approval).
  Library `judge_script` on an already-imported object does not.
- Bytes of the locked tool's implementation (AST canon, else bytecode).
  The live check is `module_hashes`. `interface_contract_hash` is derived
  from the same JSON for diffs; editing only `iface` in the lock file is
  not an independent second gate.
- Local project `.py` files reached by **static** `import` / `from` in the
  tool file (not stdlib, not site-packages, not `acid_engine`). Stored as
  `dep:<path>` in `module_hashes`. `importlib.import_module`, `__import__`,
  `exec`, and `eval` are not followed. `lock` prints a warning when those
  appear in the AST.
- Judge contour listed in `runtime_hashes` (`worker.py`, `cli.py`,
  `python_runtime.py`, `runner.py`, `resolve.py`, `implementation_canon.py`,
  `local_deps.py`). The supervisor puts the trusted package on
  `PYTHONPATH` first, not the user `cwd`.
- Local deps are sealed from **one read** of each file compared to the
  locked hash, then those bytes are executed. A swap between check and
  use is FAIL. Concurrent `judge_script` of two tools that both import
  `helper.py` does not share a `sys.modules` slot.
- `python_version` (major.minor) and `canon_kind` in the lock's `toolchain`.
  AST: neighboring CPython minor (±1) is accepted. Bytecode: exact match.
  Distant versions FAIL with "re-take the lock", not module_hash.
- Ed25519 on a receipt file, local keys only.

## Out of perimeter (will not treat as bugs)

- Shell / `bash` / any process the agent starts outside `judge`.
- What the body does after PASS: fs, net, subprocess. No isolation.
- `Policy.pure` / declared_pure: not instrumented. A write to disk PASS-es
  unless the body itself records effects.
- Imports from the standard library or from site-packages.
- Dynamic import (`importlib.import_module`, `__import__`, `exec`, `eval`):
  not pinned; `lock` warns.
- MCP / Cursor / Copilot hooks (one harness: Claude Code PreToolUse bind).
- Cosmetics that change AST (renaming a local variable) — that is FAIL by design.

## Reproduce

[attacks/](attacks/README.md) (matrix). [ATTACK.md](ATTACK.md) (manual copies). [TRUST.md](TRUST.md) (TCB).
Helper-module swap: `tests/integration/test_local_deps.py`.
Import-time side effect: `tests/integration/test_import_time.py`.
Dependency TOCTOU / undeclared helper: `tests/integration/test_toctou.py`.
Concurrent same-named helpers: `tests/integration/test_concurrent_helpers.py`.
