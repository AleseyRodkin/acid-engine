# AcidEngine — state

**Repository:** https://github.com/AleseyRodkin/acid-engine-2.0
Law: METHOD.md. Bones queue (archive): docs/archive/PLAN.md. Product queue: COMMERCIAL.md.

## Snapshot 12.09.2026

0.2 build: one face, Acid Judge. Not zip `8e1b2a7`.

## Done

1–21. Contour up to `judge_script` (body hash, SKIPPED, plan.lock, bones, JSON blank).
22. Audit: plan+iface together; obs.status in the gate; Composite external lock.
23. One hash canon after materialize; CompositeResult.conformance is the graph verdict.
24. `rust/acid-judge` bind → python worker → verdict. Without worker SKIPPED.
25. Identity: ArtifactRef not in the hash. CLI `run --script` without `--plan` → SKIPPED.
26. `container_blank` carries data; examples find the repo root themselves; ARCHITECTURE is an archive, not a plan.
27. Worker: `acid_engine.worker` identify/run, no PASS/FAIL.
28. AST canon is `unparse`. Showcase `n_plus_one.plan.json` = live body.
    cargo ≥ 1.75, lockfile v3. Rust verdict: type/status/pure/latency.
29. C0: README Acid Judge; CLI `judge` = `run --script --plan`. No receipt yet.
30. C1: `acid_engine/receipt.py`, `judge --receipt`. No proven_pure.
31. C2: `locks/index.json` + `.github/workflows/acid-judge.yml`. Without a plan it does not judge.
32. C3: five tools in `examples/tools/` + plan.json; index bones+tools.
33. C4: Claude Code PreToolUse, bind only. No MCP. Pre is not PASS.
34. C5: `acid_engine locks --index`. Body vs lock, not execution.
35. C6: Ed25519 on the receipt canon. `receipt --verify`. Not Sigstore.
36. C7: API=CLI. `judge_script` / Pipeline without plan+iface → SKIPPED. Self-lock is not a verdict.
37. H1–H5: binary without worker → SKIPPED. Observation without a worker is not a verdict.
38. 0.2: ARCHITECTURE in `docs/archive/`. Threat model on the showcase. `acid-judge` is a supervisor, not a second canon.
    CI: pytest 3.11/3.12 + locks + cargo. `toolchain` in lock JSON next to identity, not in the hash.
39. Three cuts: property without hypothesis — skip; `init`/`validate` hidden from `--help`; supervisor pins SHA-256 of `worker.py` before identify.
40. Runtime contour: `runtime_hashes` on `worker.py` + `python_runtime.py` + `runner.py` + `implementation_canon.py`. `locks --index` without a pin → FAIL.
41. `judge_script` without `toolchain` → SKIPPED. Incomplete pin → FAIL. `judge_script_from_lock` reads the lock JSON.
42. Showcase: market phrase (not an MCP gateway), [ATTACK.md](ATTACK.md), tiers in COMMERCIAL without prices. Second hook not started.
43. `toolchain.canon` = `python.ast.v1` next to identity. `level0`/`level4`/`services` in `research/`, same import path.
44. Showcase: trust continuity. FAIL says “did not run”. `diff` is inspection, not a verdict. MCP and capability not started.
45. `run` hidden from `--help`. Contour + `cli.py`/`resolve.py`. `execute_plan` without toolchain → SKIPPED. Receipt carries toolchain. Supervisor is a Release binary.
46. CLI `acid-judge` after `pip install`. Reusable Action `uses: AleseyRodkin/acid-engine-2.0@…`. Windows/macOS — `release-bins`, not this sandbox.
47. Package 0.2.3 = tag `v0.2.3`. `release-bins` has `contents: write`. Action defaults to bind, not judge.
48. `locks --judge` executes and writes a receipt. Action `judge: true` turns that on. Default without the flag is bind.
49. CI blocks ruff and mypy --strict alongside pytest. A linter outside the workflow is fail-open.
50. 0.2.5: local imports in `dep:`; `python_version`/`canon_kind` checked; `pure` = declared_pure; contour + `local_deps.py`.
51. 0.2.6: dynamic import — warning on lock, not a pin. `dependency_hash` expected/actual are file hashes.
52. 0.2.7: supervisor resolves the contour from the package / `ACID_ENGINE_ROOT`, not from a foreign repo cwd. Toolchain action by SHA. `interface_contract_hash` is not an anchor.
53. 0.2.8: product is execution integrity (wedge), not AcidEngine-OS. Attack matrix + TCB. Do not open a second harness (Copilot) in that commit.
54. 0.2.9: Approved-to-Executed wording. Receipt is execution evidence, not SLSA. `evidence.missing` without a risk score. Copilot/MCP not opened.
55. 0.2.10: pre ≠ post. demo.sh. seal local deps. symlink claimed. env/site-packages out. Copilot still closed.
56. 0.2.11: interop primitive. Four surfaces. Receipt context optional. No platform adapters.
57. 0.2.12: documentation is English-only.
58. 0.2.13: comments, docstrings, CLI help in English.
59. 0.2.14: source_hash before import; seal against locked dep hashes, one read; supervisor PYTHONPATH is the trusted package, not cwd.
60. 0.2.15: PyPI name is `acid-judge`. Import remains `acid_engine`. Do not upload over `pypi.org/project/acid-engine`.
61. 0.2.16: hook and worker do not import until `source_hash` matches. Missing pin on the worker is an error, not a load.
62. 0.2.17: committed example locks are CPython 3.11 (AST neighbor ±1). Do not lock on 3.10.
63. 0.2.18: sealed local imports are per-judge context, not a shared `sys.modules` name.
64. 0.2.19: ArtifactRef does not import until source/body hash matches. Same function + extra module-level payload is `source_hash`, not `body_hash`.

Phases 1–6 closed. Phase 7: `rust/acid-judge` supervisor: bind → python worker → verdict.
Without a worker — SKIPPED. The worker does not write a verdict. Body hash is Python canon only.

Do not: STOL, JS/WASM, proven_pure, SaaS, markdown parser, a web preview of the core.
