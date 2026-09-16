# AcidEngine 0.1 — bones plan

> **Archive.** The 0.1 builder queue, not the live product. Law is [METHOD.md](../../METHOD.md). Face: [README.md](../../README.md). Product queue: [COMMERCIAL.md](../../COMMERCIAL.md).

Brief for the builder. Law is only [METHOD.md](../../METHOD.md).
ARCHITECTURE.md is not a plan (the “OS” tail before the 21.08 narrowing). Archive: [ARCHITECTURE.md](ARCHITECTURE.md).

**Date:** 31.08.2026
**Repo:** https://github.com/AleseyRodkin/acid-engine
**Start HEAD:** `8e1b2a7`
**Python ≥ 3.11, 0 runtime dependencies**
**Tests at start:** 165 passed

The queue is strict. The builder starts at phase 1. Not Rust, not README, not ARCHITECTURE.

```text
1 blank → 2 ArtifactRef → 3 JSON loader → 4 dumb lid →
5 bones fixture → 6 judge entry → 7 Rust judge
```

The bones work queue ends at 7. Seventh: the binary does
`bind → run python worker → verdict`. Lockfile v3, cargo ≥ 1.75.
There is no phase “write a prohibition into code”.

## Product shape

A personal architecture experiment. Not a commercial mill.
STOL (lab) is someone else’s project: not a stand, not a fixture, not an example.

Four bones + a judge. Implementation and runtime are meat; they are not in the frame.

| Bone | Role |
|---|---|
| Contract | promise: who, input, output, rules |
| Container | a data snapshot on a port |
| Script | one step: container → container + trace |
| Graph | who follows whom (fan-in > 1 without merge is forbidden) |
| Judge | body imprint, lock before run, fact, verdict |

Success: no fifth bone; the body does not write the law; the author of the body does not patch the judge.

Do not write in README until it runs: “a scaffold for any project”, “any language”, “a judge in Rust”, “a development OS”.

## Law (must not break)

If this brief disagrees with METHOD.md — METHOD is right. AI is not the arbiter. Observed ≠ Proven.

- Hash of `ScriptModule` / `AsyncScriptModule` = declaration + body. Canon: AST, else bytecode. Closures and defaults are in.
- Body canon: `acid_engine/level2/implementation_canon.py`. Hash: `canonical_serialize` + SHA-256 → `content_hash_of`.
- No execution → not PASS. Not enough facts → SKIPPED.
- `execute_plan` / `replay_run` check the hash **before** run. No hashes in the lock → SKIPPED. Mismatch → FAIL, do not run the body.
- `bool ≠ int`. The core does not print stdout. Empty effects ≠ proven pure. `pure=True` + effects → FAIL.
- CLI: load → resolve → execute. `run --script` through `execute_plan`. Markdown specs are not parsed.
- `replay_run` without `expected_output` → SKIPPED. `find_record` is lookup, not rollback.

Guard tests: `tests/unit/test_identity_hash.py`, `test_plan_lock_bind.py`, `test_purity_boundary.py`; `tests/architecture/test_invariants.py`.

## Phases

| Phase | Point | Done |
|---|---|---|
| 0 | Shape: PLAN.md, CONSTITUTION. Do not rewrite METHOD | do not repeat |
| 1 | `level2/blank.py` + `tests/unit/test_blank.py`. Identity without changing `_identity_dict` | blank hash = content_hash; 165 still live |
| 2a | ArtifactRef beside; `artifact` optional; hash as now | `49a7cb3`+: `artifact.py`, hash without new keys |
| 2b | Reference instead of fn. No python language → not PASS. Broken reference → FAIL | resolve.py: python file+entry; unknown language FAIL; missing SKIPPED |
| 3 | JSON handwriting, CLI `.json`, `.md` refused | blank_loader.py; JSON+py one hash; max_latency_ms → float |
| 4 | Lid: Pipeline/Composite through execute_plan | no public PASS without a lock |
| 5 | `examples/bones/` dict n:3→n:4 + .json + integration | n_plus_one.py/.json; JSON hash = callable |
| 6 | `judge.py` facade → `execute_plan` | judge_script; CLI and Pipeline through it |
| 7 | Rust only after 1–3 are stable | bind → python worker → verdict; without worker — a mirror; cargo ≥ 1.75, lockfile v3 |

## Do not (this is not a phase and not code)

A fence for the next chat, not a sprint. This is not committed to the repo as a feature.

- STOL — someone else’s project: not a stand, not a fixture, not an example
- JS body, WASM — a second runtime
- JSON Schema as identity canon
- `proven_pure` (Observed ≠ Proven)
- SaaS / self-hosting / “development OS”
- a markdown-spec parser

Law that the runtime already enforces lives in METHOD.md. This list exists so extra work is not started.

### Phase 1 — details

File `acid_engine/level2/blank.py`.
Functions: `script_identity_blank`, `container_blank`, `plan_blank`, `graph_blank`, `observation_blank`, `conformance_blank`, `parse_script_identity_blank`.

`script_identity_blank` = `_identity_dict` without `content_hash`.
A `{schema,kind,identity}` wrapper is allowed; schema/kind are not in the hash.

Equality: `content_hash_of(script_identity_blank(script)) == script.content_hash`

Must not: pydantic, JSON Schema, change `ScriptModule.__init__`, change `_identity_dict` membership, Rust, YAML, CLI, new input types.

Do not break the lock key (`_locked_hash_for`).
Do not touch `cmd_validate` in phases 1–3.

Do not start N+1 until N is green.

Check:

```text
PYTHONPATH=. python -m pytest tests -q
```
