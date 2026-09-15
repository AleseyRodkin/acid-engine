# Changelog

## 0.2.14 — 2026-09-16

- `source_hash` of the exec target is compared to the lock **before import**. Mismatch → FAIL, the file is not imported. Missing pin → SKIPPED.
- Those bytes are pinned: load/exec uses the hashed snapshot, not a second disk read.
- `seal_local_deps` compares one read of each local import to the **locked** `dep:` hash (empty lock still walks; undeclared helper → FAIL).
- Supervisor: trusted package on `PYTHONPATH` first, worker spawned by absolute path, `python -P` to locate the package (cwd last).

## 0.2.13 — 2026-09-16

- Remaining Python comments, docstrings, and CLI `--help` translated to English.

## 0.2.12 — 2026-09-16

- Documentation is English-only (README, METHOD, PLAN, COMMERCIAL, CONSTITUTION, TUTORIAL, glossary, archive).

## 0.2.11 — 2026-09-16

- Primitive, not a control plane. Four surfaces: CLI, library, hook, receipt ([INTEROP.md](INTEROP.md)).
- Receipt `context.agent` / `context.repository` optional. Not identity. Copilot/APort adapters not opened.

## 0.2.10 — 2026-09-16

- Pre-execution bind ≠ post-execution PASS. README is a landing page; `./demo.sh` is the 60s proof.
- Local deps sealed from hashed bytes before run (lazy-import TOCTOU).
- Symlink followed; retarget after lock is FAIL.
- Env and site-packages stay out of identity. Copilot not opened.

## 0.2.9 — 2026-09-16

- Claim is approved-to-executed, not a generic execution-integrity platform.
- Receipt `evidence.missing`: facts absent on SKIPPED. Empty on PASS/FAIL. Not a risk score.
- Paid path is evidence, not hosted lock registry. Copilot not in this release.

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
