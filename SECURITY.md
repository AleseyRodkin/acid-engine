# Security

Report a vulnerability privately: open a GitHub Security Advisory on
[AleseyRodkin/acid-engine-2.0](https://github.com/AleseyRodkin/acid-engine-2.0)
or email the account that owns that repository. Target response: 7 days.

This is a fail-closed **file lock** on a locally approved Python-tool body
(and its local `.py` imports, and the judge contour). It is not a sandbox
and not an MCP gateway.

## In perimeter

- Bytes of the locked tool's implementation (AST canon, else bytecode).
- Local project `.py` files that the tool file imports (not stdlib, not
  site-packages, not `acid_engine`). Stored as `dep:<path>` in `module_hashes`.
- Judge contour listed in `runtime_hashes` (`worker.py`, `cli.py`,
  `python_runtime.py`, `runner.py`, `resolve.py`, `implementation_canon.py`,
  `local_deps.py`).
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
- MCP / Cursor / Copilot hooks (one harness: Claude Code PreToolUse bind).
- Cosmetics that change AST (renaming a local variable) — that is FAIL by design.

## Reproduce

[ATTACK.md](ATTACK.md). Helper-module swap: `tests/integration/test_local_deps.py`.
