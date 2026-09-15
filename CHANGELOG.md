# Changelog

## 0.2.8 — 2026-09-16

- Wedge language: execution integrity, not a platform. SKIPPED is a first-class state.
- Attack matrix: [attacks/](attacks/README.md). TCB: [TRUST.md](TRUST.md).
- `locks --index` prints Tools checked / Failed / Execution integrity.

## 0.2.7 — 2026-09-15

- Rust supervisor locates the judge contour via `cwd/acid_engine/`, `ACID_ENGINE_ROOT`, or the installed package — not only the user project cwd.
- `dtolnay/rust-toolchain` pinned to commit SHA in CI and release-bins.
- SECURITY.md: `module_hashes` is the trust anchor; `interface_contract_hash` is derived.
- COMPATIBILITY.md: 0.2.x lock/CLI stability.

## 0.2.6 — 2026-09-15

- `lock` warns on `importlib.import_module` / `__import__` / `exec` / `eval`: local deps cannot be fully pinned.
- `dependency_hash` expected/actual are file hashes, not name lists.

## 0.2.5 — 2026-09-15

- Local project imports of a tool are hashed (`dep:` in `module_hashes`). Swap helper.py → FAIL before run.
- `python_version` and `canon_kind` are checked; mismatch says re-take the lock, not module_hash.
- `Policy.pure` documented as declared_pure; runtime still does not instrument I/O.
- lock/judge print the same two hashes: `interface_contract_hash` and `plan_content_hash`.
- Body-crash message no longer claims the body was not executed.
- Contour pin includes `local_deps.py`. CI ruff covers examples and research.
- SECURITY.md, CONTRIBUTING.md, issue/PR templates. CLI prog is `acid-judge`.

## 0.2.4 — 2026-09-12

- `locks --judge` and Action `judge: true`. Default Action remains bind-only.

## 0.2.3 — 2026-09-12

- Package version matches the git tag. `release-bins` has `contents: write`.
