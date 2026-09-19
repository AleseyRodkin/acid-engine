# Changelog

## Unreleased

- PyPI canon is `acid-judge`. This tree is not published as `acid-engine`. Yank 0.2.21–0.2.22 on that name; `acid-engine==0.2.0` stays the data-contracts archive.
- Composite Action Verify step passes `index` / `judge` / `receipts` through env, not `${{ inputs.* }}` inside `run:`.
- `cli.py` is out of `runtime_hashes`. A CLI help-text patch does not reshoot locks. Canon / body / helper swap still FAIL before run.
- Empty or unknown `output_type` is SKIPPED, not PASS. `bool ≠ int` is still FAIL. Same in Python and Rust.
- Hidden `init` / `validate` / `run` are gone. `--help` is the whole CLI.
- INTEROP: `judge_script` on an already-imported callable is not a file gate and does not hash `co_code`.

## 0.2.22 — 2026-09-16

- `replay_run` uses the same verified execution as `execute_plan`: runtime pin, interface bind, body/dep hashes, `seal_local_deps`, then run. Poisoned contour or a swapped helper does not execute.
- `replay_run` / `replay_from_record` take `iface` and `toolchain`. Missing either is SKIPPED, not a silent bind-only run.
- Library `judge_script` still does not re-hash an already-imported callable. Embed via `judge_script_from_lock`. Signed lock / empty-hash SKIPPED / `_PINNED_SOURCE` snapshots: not this release.

## 0.2.21 — 2026-09-16

- GitHub repository is [`acid-engine`](https://github.com/AleseyRodkin/acid-engine) (was `acid-engine-2.0`). Old URLs redirect.
- The 2026 data-contracts tree is [`acid_engine_archive`](https://github.com/AleseyRodkin/acid_engine_archive) (was `acid_engine`).
- PyPI: `acid-judge` stays. `acid-engine` 0.2.21+ is this product (same files). `acid-engine==0.2.0` was the archive.
- Import remains `acid_engine`. CLI remains `acid-judge`. Contour unchanged.

## 0.2.20 — 2026-09-16

- PreToolUse: a tool that reached the hook and is not in the index is **deny** (not enough facts is not allow). The settings matcher is how Bash / Read never reach the hook.
- Hook lookup is exact entry id or a resolved script path. Basename is not identity. Same stem plus a different file, or a stolen id with a foreign path, is deny.
- `demo.sh` does not set `PYTHONPATH`. Installs the package if it is not importable.
- CI composite Action pins `actions/checkout`, `actions/setup-python`, `actions/upload-artifact` to commit SHAs. `pypa/gh-action-pypi-publish` stays on the `v1.13.0` tag (GHCR image is published for the tag, not a SHA).
- macOS supervisor artifact is `acid-judge-macos-arm64` (`macos-latest` is Apple Silicon).
- Library `judge_script` still does not re-hash an already-imported callable. Embed via `judge_script_from_lock`. Contour still includes `cli.py` (a CLI patch reshoots locks). Signed lock / sandbox / MCP / branch protection: not this release.

## 0.2.19 — 2026-09-16

- `ArtifactRef` does not import until `source_hash` / `body_hash` match a snapshot of the file. Same flow as the root tool: snapshot → hash → compare → pin → exec pinned bytes.
- `body_hash` is the AST canon of the entry callable (previewed from file bytes, no exec). `source_hash` is SHA-256 of those bytes — same function plus extra module-level payload fails this, not `body_hash`.
- Empty hashes still load (phase 2b). Mismatch does not run module-level side effects.
- Signed lock, `ExecutionSnapshot` type, sandbox, MCP: not this release.

## 0.2.18 — 2026-09-16

- Sealed local imports are bound per judge context, not under a shared `sys.modules` name. Two tools that both have `helper.py` cannot PASS each other's body under concurrent `judge_script`.
- Same uniqueness idea as CLI `id(source)` for the tool file.
- Rust tests serialize `ACID_ENGINE_ROOT` so parallel cargo test does not race.

## 0.2.17 — 2026-09-16

- Example locks retaken on CPython 3.11. A 3.10 lock fails 3.12 (AST neighbor is ±1). Contour is the same as 0.2.16.

## 0.2.16 — 2026-09-16

- PreToolUse hook compares `source_hash` before import. A swapped tool file is deny; top-level side effects do not run.
- Worker without `source_hash` refuses to load (not a quiet exec).
- `origin_source_hash` and local-dep AST reads use the pinned snapshot, not a second disk read.
- Showcase commands use `acid-judge` after install, not `PYTHONPATH=.`. Hidden `run` is not in COMMERCIAL start.
- 0.1 bones plan moved to `docs/archive/PLAN.md`.

## 0.2.15 — 2026-09-16

- PyPI distribution name is `acid-judge`. Import stays `acid_engine`. CLI stays `acid-judge`.
- Does not overwrite [acid-engine](https://pypi.org/project/acid-engine/) (data contracts, Apache 2.0).
- Trusted Publishing workflow: `.github/workflows/pypi.yml`.

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
