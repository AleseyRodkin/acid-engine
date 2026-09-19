# Acid Judge

Verify what your AI agent actually executes.

Acid Judge verifies that the code approved for an AI agent is the code that actually executes.

Not a policy gate. A policy gate can ALLOW `compute_amount` after the file on disk has already changed. This gate asks a different question: **is this still the approved artifact?**

**Before execution:** the implementation bound for execution matches the approved artifact. The Claude Code hook is this step. Pre ≠ PASS.

**After execution:** Acid Judge records evidence that the verified implementation ran, and whether the observation conforms to the contract. PASS lives only here.

We don't tell you that your code is safe. We tell you whether it is the code you approved.

An agent can write or change a tool. Acid Judge does not have to believe it. It checks that the approved body is what will run, then checks the observation against the contract. Not enough facts → SKIPPED, not PASS.

**Approved-to-executed integrity** — Python-first, local, open source, no sandbox, no LLM, deterministic.

Independent execution-integrity layer. Policy asks *allowed?*. This layer asks *which implementation?*. A sandbox asks *what can the process do?*. Embed this component; do not replace those layers.

```text
policy / authorization
        ↓
Acid Judge     ← this layer
        ↓
runtime / sandbox
```

Python is the first adapter, not the category. Four surfaces: [INTEROP.md](INTEROP.md).

Trust continuity: approved → locked → verified → executed → observed → receipt. Not a checksum feature. The trust layer sits between the agent and the Python tool it is about to run.

```text
PASS     = enough facts to claim the approved body ran
FAIL     = mismatch; the body was not the approved one (or the observation failed)
SKIPPED  = not enough facts. SKIPPED is not PASS.
```

The lock catches a tool-file swap between `lock` and `judge`. It does not catch a shell, and it does not catch files outside `runtime_hashes`.

Fail-closed gate of a locked Python-tool body. Catches a file swap between `lock` and `judge`. Does not catch a shell, does not sandbox the body after PASS, is not a development OS. Not SaaS, not `proven_pure`.

Package **0.2.25**. MIT core. Supervisor binaries: GitHub Releases (`linux-x86_64` / `windows-x86_64` / `macos-arm64`), no local `cargo`. After `pip install` the binary finds the contour in the installed package, not in `cwd`.

Not an MCP gateway. Gateways watch poisoned *tool descriptions* on the network. Acid Judge checks *file bytes* of a locally approved Python tool (and the judge contour) right before the call. Complementary layer, not a substitute.

Proof: [attacks/](attacks/README.md). Manual copies: [ATTACK.md](ATTACK.md). TCB: [TRUST.md](TRUST.md). Runtime law: [METHOD.md](METHOD.md).

## 60 seconds

```bash
./demo.sh
```

Honest `compute_amount` is PASS. The swapped body is blocked. No sandbox, no LLM.

## Verify it yourself

No signup. No cloud. No trust required.

```bash
git clone https://github.com/AleseyRodkin/acid-judge-smoke.git
cd acid-judge-smoke
./smoke.sh
```

Run the smoke test: [acid-judge-smoke](https://github.com/AleseyRodkin/acid-judge-smoke).
The product repository explains Acid Judge. The smoke repository is the proof.

## Install

```bash
pip install acid-judge==0.2.25
acid-judge lock --script FILE --out LOCK.json
# commit LOCK.json and locks/index.json
acid-judge locks --index locks/index.json
acid-judge judge --script FILE --plan LOCK.json --input '...'
```

```yaml
- uses: AleseyRodkin/acid-engine@v0.2.25
  with:
    index: locks/index.json
    judge: true
```

Swapped body is not PASS. Proof: [acid-judge-smoke](https://github.com/AleseyRodkin/acid-judge-smoke).


## What it protects

- Tool body swap between `lock` and `judge` (if a hook or CI checks the hash)
- Static local `.py` imports (`dep:`). `importlib.import_module` / `exec` / `eval` are not pinned — `lock` warns
- Judge contour (`runtime_hashes`)
- Symlink retarget after lock (bytes of the followed path)
- Bind-then-disk-write of a lazy local import (sealed against the **locked** hash, one read)
- Two tools that both have `helper.py` judged concurrently (per-context seal, not a shared `sys.modules` name)
- Top-level code in the tool file: CLI, supervisor, hook, `locks`, and `diff` compare `source_hash` **before import**. Mismatch → the file is not imported.
- `ArtifactRef` / JSON blank: `source_hash` (file bytes) and `body_hash` (entry AST) are compared to a snapshot **before** exec. Empty hashes still load. Same function plus extra top-level code is `source_hash`.
- PreToolUse hook: a tool that reached the hook and is not in the index is **deny**. Lookup is exact id or resolved script path, not basename. The settings matcher is how Bash never hits the hook.

Renaming a local variable changes the AST canon — FAIL. Comments and blank lines are not in the canon.
The lock is an imprint of a specific toolchain. `python_version` and `canon_kind` are checked; a mismatch is FAIL with "re-take the lock", not "the body was swapped".
The supervisor checks SHA-256 of the contour (`worker.py`, `python_runtime.py`, `runner.py`, `resolve.py`, `implementation_canon.py`, `local_deps.py`, `cli_judge.py`) before identify. No pin → SKIPPED. Mismatch → FAIL. `locks --index` and CLI `judge --plan` without a pin → FAIL. `judge_script` without `toolchain` → SKIPPED. Incomplete pin → FAIL. `judge_script_from_lock` reads pins from the lock JSON. `cli.py` is not in the pin: argparse / help-text patches do not reshoot locks. PASS is decided in `cli_judge.py`.

## What it does not protect

- Shell outside `judge`
- What the body does after PASS (fs / net / process). No isolation.
- `importlib` / `exec` / `eval` (lock warns)
- site-packages / stdlib supply chain (separate control: SBOM / SLSA)
- Environment variables (not part of implementation identity)
- `judge_script` on an already-imported `ScriptModule` (library). The CLI, supervisor, and hook hash the file before import. `lock` loads the file you present — that is how a lock is taken.

Threat model: [SECURITY.md](SECURITY.md). Coverage: [attacks/](attacks/README.md). TCB: [TRUST.md](TRUST.md).

## Three commands

| Command | Role |
|---|---|
| `lock` | lock the body |
| `judge` | bind before run + verdict |
| `receipt` | `judge … --receipt FILE` — Observation + PASS/FAIL/SKIPPED, no `proven_pure` |

`locks --index` — live body vs lock in git. Does not execute, not hosted.
`diff --script --plan` — approved vs live table. Does not execute, not PASS.
`receipt --sign` / `receipt --verify` — Ed25519 on the receipt canon, local openssl. Not Sigstore.

The product is Acid Judge. Repository: [`acid-engine`](https://github.com/AleseyRodkin/acid-engine). Import: `acid_engine`. CLI: `acid-judge`.
PyPI: `pip install acid-judge`. Do not `pip install acid-engine` for this product — that name is the archived data-contracts tree (`acid-engine==0.2.0`). Releases 0.2.21–0.2.22 on that name are yanked.

Showcase:

```bash
acid-judge lock --help
acid-judge judge --script examples/bones/n_plus_one.json --plan examples/bones/n_plus_one.plan.json --input '{"n": 3}' --receipt /tmp/bones.receipt.json
acid-judge judge --script examples/bones/n_plus_one.json --input '{"n": 3}'
```

Why not PASS, short: wrong body / no execution / pure but effects / type mismatch / lock not passed.

License: [LICENSE](LICENSE).

## Supervisor, not a second canon

The `acid-judge` binary is a supervisor: identify → bind → run worker → verdict.
Only the Python canon hashes the body. Without a worker — SKIPPED, not PASS. Observation without a worker is not a verdict.
Contour: `cwd/acid_engine/` (this repository), else `ACID_ENGINE_ROOT`, else the installed package. Not a foreign project's `cwd`.
Linux/Windows/macOS: [Releases](https://github.com/AleseyRodkin/acid-engine/releases).

0.2.x compatibility: [COMPATIBILITY.md](COMPATIBILITY.md).

## Checks

```bash
pip install -e ".[dev]"
python -m pytest tests -q
python locks/ci_judge.py
cargo test --locked --manifest-path rust/acid-judge/Cargo.toml
```

CI: [.github/workflows/acid-judge.yml](.github/workflows/acid-judge.yml) — pytest (3.11/3.12), `locks/index.json`, cargo. The job fails if a tool is not PASS. Receipt is an artifact. No `plan` in the index → does not judge.

Dev: `pip install -e ".[dev]"` — pytest, ruff, mypy.

```bash
ruff check acid_engine tests examples
mypy --strict acid_engine locks/ci_judge.py
```

## What holds the gate

- Hash = declaration + body canon (`ast.unparse`, else bytecode). `ArtifactRef` is not identity.
- `plan.lock` before run. Mismatch → FAIL, the body does not run.
- No execution → not PASS. Not enough facts → SKIPPED. `bool ≠ int`.
- The worker does not write PASS/FAIL. `judge_script` without plan+iface → SKIPPED (self-lock is not a verdict). `lock --script` only writes JSON. `judge_script` on an already-imported object does not re-check `source_hash` — the CLI and supervisor do, before import.
- The `acid-judge` binary without `worker` does not judge: SKIPPED.

Five tools: [examples/tools/](examples/tools/) (`clean_text`, `normalize_id`, `compute_amount`, `route_ticket`, `emit_forecast_card`) — in [locks/index.json](locks/index.json) with bones.

One hook: [examples/hooks/pre_tool_use.py](examples/hooks/pre_tool_use.py) — Claude Code PreToolUse, bind only. Foreign hash → deny. Unknown tool that reached the hook → deny. Pre ≠ PASS. No MCP.

## Not in 0.2

Sandbox, MCP hook, Sigstore SaaS, hosted registry, markdown specs, WASM, JS bodies, STOL, prices, a second hash canon in Rust.
