# Changelog

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
