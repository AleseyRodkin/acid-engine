# Changelog

## Unreleased

## 0.2.33 — 2026-09-20

- After seal, `importlib.reload` of a locked helper re-execs the sealed bytes. A later disk write is not PASS.
- Judge FAIL if `detect_dynamic` is not empty (`importlib.import_module`, `__import__`, `exec`, `eval`). Lock still warns. `allow_dynamic: true` on the lock is 0.2.32 (not pinned). This is not “dynamic is closed”: other loaders are out of the detector.
- Contour files changed. Locks reshot on CPython 3.11.

## 0.2.32 — 2026-09-20

- JSON blank: one parse; pin JSON + `.py`. After the source_hash gate, swapping `implementation.file` does not exec the new file.
- Local dep seal: discover + verify all hashes, then `ModuleType` placeholders, then exec pinned bytes. Cycle A↔B goes through placeholders. A mismatch does not exec a good neighbor.
- Supervisor: both identify and run spawn from the hashed worker bytes (`python -c`), not a second open of the path. Worker is not embedded in the binary. CPython and `__init__.py` are not pinned.
- Locate the package via sys.path (site-packages / `ACID_ENGINE_ROOT`), without importing it.
- README / SECURITY: empty `source_hash` does not load.
- Contour files changed. Locks reshot on CPython 3.11.

## 0.2.31 — 2026-09-20

- Package `__init__.py` seals as the import name (`pkg/__init__.py` → `pkg` + `__path__`). Lock key stays the file path (`dep:pkg/__init__.py`). `from pkg import sub` is walked.
- `locks --judge` keeps the first plan JSON snapshot. Changing the file after bind does not re-bind.
- Action driver receipts on PASS use the supervisor payload / `dummy_script`. No second `load_script_from_file`.
- Execute paths wrap `with sealed_deps` and pop only this mapping's `acid_dep_*`. `seal_local_deps` does not reset on success (that would unseal before run).
- `load_script_lock` rejects a crooked `plan_content_hash`.
- `ArtifactRef` without `source_hash` does not exec. JSON blanks still snapshot and fill the digest before load.
- Contour files changed. Locks reshot on CPython 3.11.

## 0.2.30 — 2026-09-20

- Pushing tag `v0.2.N` runs the gate then `gh release create --verify-tag`. Do not create the GitHub Release first. No minisign.
- Supervisor `bind()` FAILs if `dependency_hashes` is set but `dep:*` was cut from `module_hashes`, or a `dep:` value is empty. Not a second hasher. Contour unchanged.

## 0.2.29 — 2026-09-20

- Supervisor seals `dep:*` on identify and run. Helper swap between those calls is FAIL, not PASS. A live local import without a hash is a worker error (FAIL, not SKIPPED).
- Async composite goes through `_prepare_execution` (bind + seal). `cmd_judge` lives in `cli_judge.py`. `action_driver.py` is in `runtime_hashes`.
- `MatchesPredicate` has an 80ms budget (subprocess; CPython `re` holds the GIL). Timeout / bad pattern / predicate exception → FAIL.
- PreToolUse verifies the index pin when present. Contour is 8 files. Locks reshot on CPython 3.11.

## 0.2.28 — 2026-09-20

- PreToolUse reads `ACID_REPO_ROOT` / `ACID_LOCKS_INDEX` (else cwd / `locks/index.json`). No `sys.path.insert` into the product tree. Package comes from pip. Matcher fragment is `YOUR_TOOL_ID`; product ids live in `claude_settings.product.fragment.json`.
- Signature of Release assets is not in this tag (`MINISIGN_SECRET_KEY` not on the publisher). Tagged Action still checks sha256.

## 0.2.27 — 2026-09-19

- Self-CI `rust` job builds `target/release/acid-judge` (MSRV 1.75, `--locked`) and runs `python -m acid_engine.action_driver` on `locks/index.json`. No GitHub Fetch. Receipts on disk. `uses: ./` stays python-cli.
- `cargo audit` is a separate job on rustc 1.88, not mixed with MSRV. No `cargo update`.
- TRUST: driver is not contour; tagged root is GitHub Release + sha256. attacks: tagged Action does not go through `cmd_judge`.

## 0.2.26 — 2026-09-19

- Supervisor binary exits 0 on PASS, 1 on FAIL, 2 on input error or SKIPPED. JSON body is unchanged.
- Release assets include `<artifact>.sha256`. Tagged Action verifies sha256sum -c; mismatch logs `checksum mismatch` and falls back to python-cli.
- Action driver is `python -m acid_engine.action_driver` (not in `runtime_hashes`). YAML has no entries loop. Supervisor path writes `receipts/<id>.json`.

## 0.2.25 — 2026-09-19

- Tagged Action (`uses: …@v0.2.n` on Linux) fetches `acid-judge-linux-x86_64` from the same GitHub release and verifies through the supervisor (`path=supervisor`). `uses: ./` and a missing asset stay `path=python-cli`. URL is not an input. Contour unchanged.
- Install block: pin, lock, index in git, Action, `locks --index`, `judge --plan`. Swapped body is not PASS. Proof is smoke.
- Cargo.toml version tracks 0.2.25; crates.io `publish = false`. Replay stays library-only.

## 0.2.24 — 2026-09-19

- RecordSchema uses the same type dictionary as conformance. Unknown `type_tag` is invalid. `True` is not `int`.
- `cli_judge.py` is in `runtime_hashes`. `cli.py` is not. Worker imports `cli_judge`, not `cli`. A help-text patch does not reshoot locks; a patch of `cli_judge.py` or `worker.py` is `runtime_hash` FAIL before run.

## 0.2.23 — 2026-09-19

- PyPI canon is `acid-judge`. This tree is not published as `acid-engine`. Yank 0.2.21–0.2.22 on that name; `acid-engine==0.2.0` stays the data-contracts archive.
- Composite Action Verify step passes `index` / `judge` / `receipts` through env, not `${{ inputs.* }}` inside `run:`.
- `cli.py` is out of `runtime_hashes`. A CLI help-text patch does not reshoot locks. Canon / body / helper swap still FAIL before run.
- Empty or unknown `output_type` is SKIPPED, not PASS. `bool ≠ int` is still FAIL. Same in Python and Rust.
- Hidden `init` / `validate` / `run` are gone. `--help` is the whole CLI.
- INTEROP: `judge_script` on an already-imported callable is not a file gate and does not hash `co_code`.
- `mypy --strict` covers `locks/ci_judge.py`.
- `COMMERCIAL.md` is positioning and the product queue. No tariff, no ICP list.

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
