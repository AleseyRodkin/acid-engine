# METHOD

AcidEngine law. If the runtime does not enforce a rule, it is not in this file
and it must not be written in the README.

Code is written by a human or an AI. The arbiter is a checkable contract, not a model.
The system has no right to claim more than it observed.

## Entities

```text
Contract ≠ Container ≠ Graph ≠ Implementation ≠ Runtime
Parameters ≠ Policy ≠ ImplementationRequirements
```

A script contract: `CONSTRAINTS` / `INPUT` / `OUTPUT` / `IMPLEMENTATION`.
These are separate fields, not one bag.

## Identity

The hash of `ScriptModule` and `AsyncScriptModule` covers the declaration **and the implementation body**.

Body canon (one):

1. AST of the source via `ast.unparse` (not `ast.dump`: node fields grow with CPython);
2. otherwise the bytecode of what actually runs.

Closures and defaults are in the hash: they are part of what runs.
A different body → a different hash. Swapping `x+1` for `x+100` with the same
declaration breaks `content_hash` and `plan.lock`.
Local `.py` files that the tool file imports (not stdlib, not site-packages,
not `acid_engine`) enter the lock as `dep:<path>` = SHA-256 of the file.
Swapping a helper with the same entry body → FAIL, do not run the body.
The exec target file (the `.py`, or `implementation.file` of a JSON blank)
enters the lock as `source_hash` = SHA-256 of those bytes. CLI `judge` /
`locks` / `diff` and the supervisor compare this **before import**.
Mismatch → FAIL, the file is not imported. Missing `source_hash` → SKIPPED.
The bytes that matched are the bytes that are imported (one read).
`judge_script` on an already-constructed `ScriptModule` does not re-read the
file: the caller already imported it.
`importlib.import_module` / `__import__` / `exec` / `eval` are not followed:
`lock` warns that local deps cannot be fully pinned. Renaming a local variable
changes the AST canon.
Body canon is one: the callable. `ArtifactRef` is a locator, not identity.
When `ArtifactRef` carries `body_hash` or `source_hash`, those are compared
to a snapshot of the file **before** exec. Mismatch → do not import.
`body_hash` is the AST canon of the named entry. `source_hash` is SHA-256
of the file bytes. Empty hashes still load. No callable → `implementation`
in identity = `{kind: missing}`.
After resolve (`materialize_script`) identity is the canon of the fn body.
Take the lock after materialize. A reference dict is not in the hash.

## Observation

After a run there is Observed.
`Observed ≠ Proven`. One clean run does not yield `proven_pure`.
`Policy.pure` is declared_pure. Runtime does not instrument I/O.
Empty `effects_observed` ≠ a proof of purity.
AI is not the arbiter.

## Gate

No execution → not PASS.
`SKIPPED` when there are not enough facts to judge.
`obs.status != completed` → not PASS (`failed` → FAIL, `skipped` → SKIPPED).
A stub cannot PASS: an unexecuted `InterfaceContract` in `Pipeline`,
a `LocalAdapter` placeholder — even on garbage input.

## CLI

`main()` / CLI contain no business orchestration beyond:
`load → resolve → execute` of an already permitted contract.

`run --script` goes through `judge_script` → `execute_plan`.
`run --script file.py` loads the `script` variable (`ScriptModule`) and runs it.
`validate` takes a `.py` with a `contract` variable. Markdown specs are not parsed.
`judge_script` / `Pipeline(ScriptModule)` without a plan+iface pair → SKIPPED.
Self-lock is not a verdict. Including in the library.
`lock_for_script` takes a lock (`lock --script`), not a path to PASS inside judge.
`run --script` without `--plan` → SKIPPED (self-lock is not a verdict).
`judge` is an alias of `run --script --plan`. Without `--script` it is not the walking skeleton.
`--plan` is lock JSON (`lock --script`). Markdown specs are not parsed.
`judge --receipt FILE` writes `acid.receipt.v1`: hashes, output, observation, verdict.
No `proven_pure`, no callable. Without `--plan` a receipt is still written — status SKIPPED.
`locks --index` compares the live body to `plan.lock`. Does not execute. Mismatch → FAIL.
`receipt --sign` / `--verify`: Ed25519 on `canonical_serialize(receipt)`, local key.
Not Sigstore. Tampering the receipt body → verify fails.

## Rust supervisor

The binary does not hash the body. One canon — Python (`implementation_canon`).
One binary entry: a worker is required.
Before identify the supervisor checks SHA-256 of the runtime contour (`worker.py`, `cli.py`, `python_runtime.py`, `runner.py`, `resolve.py`, `implementation_canon.py`, `local_deps.py`) against `runtime_hashes` and `worker_hash` in the request/lock.
The contour is sought in `ACID_ENGINE_ROOT`, else the installed package (`python -P -c "import acid_engine"`), else `cwd/acid_engine/` last. Not in a foreign project's `cwd` first.
No `worker_hash` or no full `runtime_hashes` → SKIPPED. Mismatch → FAIL. The runtime hash is not in body identity.
`locks --index` without `worker_hash` / `runtime_hashes` → FAIL, not fail-open.
CLI `judge --plan` checks `source_hash` against the exec target **before import**, then the same runtime pins. `source_hash` mismatch → FAIL, the file is not imported. Missing `source_hash` → SKIPPED.
The PreToolUse hook does the same gate before bind. The worker refuses to load without `source_hash`.
Supervisor `PYTHONPATH` is the trusted package first, not the user `cwd`. The worker is spawned as an absolute path, not `python -m`.
`judge_script` without `toolchain` → SKIPPED (`runtime not pinned`). With `toolchain` but without full `runtime_hashes` → FAIL.
`judge_script_from_lock` reads plan+iface+toolchain from the lock JSON.
`execute_plan` without `toolchain` → SKIPPED. This is not a public entry: outside, `judge_script` / CLI.
identify → bind → run worker → verdict.
No worker → SKIPPED. Observation without a worker is not a verdict.
After run: status, output_type, pure, latency.
Semantic/schema/invariants — Python only.
The worker does not write PASS/FAIL. The author of the body does not patch the judge.
Not a runtime and not WASM. cargo ≥ 1.75, lockfile v3.

## Types

`bool ≠ int`. `True`/`False` do not pass as `int`.

## Graph

Fan-in > 1 in Composite is forbidden until there is a merge contract.
Silently taking only `preds[0]` is not allowed.

## Observation

The core does not print to stdout. Observation logging is opt-in via a passed logger.

## Blank

`container_blank` carries `data`. Without data a step cannot be built from a blank.
`parse_container_blank` checks `content_hash` against data. Mismatch is an error.

## Pipeline

`Pipeline.execute` returns `PipelineResult`: `data`, `observation`, `conformance`.
`Pipeline.execute` for ScriptModule goes through `execute_plan` / `plan.lock`.
Interface without execution → SKIPPED, `data=None`, `observation=None`.

## CLI input

`--input`: int, JSON (list/dict), or string. Not int only.

## History

`replay_from_record` returns `ConformanceResult`, not bool.
The output fact is `expected_output` or `record.output_data`. Mismatch → FAIL.
`find_record` is lookup by `run_id` only. There is no state rollback.

## Plan.lock

`execute_plan` / `replay_run` check `script.content_hash` against `plan.module_hashes`
**before** execution. Mismatch → FAIL, the body is not run.
CLI / supervisor also check `source_hash` **before import**.
No hashes in the lock → SKIPPED.
`interface_contract_hash` is checked too.
Local deps are sealed from **one read** compared to locked `dep:` hashes, then those bytes are exec'd. Undeclared local import → FAIL. Sealed imports are per-judge context, not a shared `sys.modules` name.
`replay_run` without `expected_output` → SKIPPED.
`execute_plan` returns `PipelineResult` (data + observation + conformance).

## Effects / DataPlane

`EffectCollector` collects `effects_observed` for a run.
`DataPlane.store` / `record_effect` is a fact.
`policy.pure=True` and non-empty `effects_observed` → FAIL.
`InMemoryDataPlane` and `FileSystemDataPlane`. Empty effects ≠ proven pure.

## Composite

`Composite.execute` returns `CompositeResult`: `data` + `observations` + `conformance`.
No `conformance.ok` — not PASS.
External `plan`+`iface` binds leaves to the lock. One without the other — do not execute.
Without a plan — SKIPPED. Self-lock is not a verdict. Including for Composite.

## CLI run

`run --script` without `--plan` is not PASS. With `--plan` — `judge_script` / a frozen lock.
Does not bypass the lock via a raw `run_script`.
`lock --script` writes lock JSON; that is not a verdict.
`diff --script --plan` compares live vs lock. Does not execute, not PASS.
In the lock JSON next to identity (not in `content_hash`) — `toolchain.python_version`, `toolchain.canon_kind`, `toolchain.canon` (`python.ast.v1` / `python.bytecode.v1`), `toolchain.worker_hash`, `toolchain.runtime_hashes`, `source_hash`.
A new canon version (`python.ast.v2`) does not silently replace old semantics: the canon name sits beside the hash; the body hash algorithm stays until the name changes and locks are re-taken.

## History

`replay_from_record` without `plan` → SKIPPED. With `plan` → `replay_run`.
