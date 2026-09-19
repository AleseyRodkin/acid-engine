# Acid Judge — product plan

Law is only [METHOD.md](METHOD.md). Do not reopen [docs/archive/PLAN.md](docs/archive/PLAN.md) (0.1 bones).

## 1. Position

**Acid Judge** is an independent execution-integrity primitive, not a control plane.
It verifies that the code approved for an AI agent is the code that actually executes.
Not a policy gate. Not an MCP gateway. Not a sandbox. Not SLSA. A neighbor of those layers, not a replacement.

Four surfaces: CLI, library, one hook, receipt. [INTEROP.md](INTEROP.md).
APort / AGT / Copilot adapters — on the caller’s request, not in 0.2.

Public contract: `lock`, `judge`, `receipt`. MIT core.

Never in this plan: SaaS-OS, self-hosting, profiles, markdown specs, `proven_pure`, a scaffold for any project, aggregator-as-product, competing with Pydantic, JS/WASM/a second language, STOL, SKIPPED→PASS, twenty adapters, MCP as a second harness, Copilot before a green Claude hook, a risk score, a published tariff.

## 2. Must not break

- Hash = declaration + body canon (`ast.unparse`, else bytecode). ArtifactRef is not identity.
- `plan.lock` before run. Mismatch → FAIL, do not run the body.
- No execution → not PASS. Not enough facts → SKIPPED. `bool ≠ int`. Unknown `output_type` → SKIPPED. pure+effects → FAIL.
- CLI `judge --script` without `--plan` → SKIPPED. The worker does not write PASS/FAIL.
- `judge_script` / Pipeline / Composite without a plan+iface pair → SKIPPED. Without `toolchain` → SKIPPED. Self-lock is not a verdict.
- Rust without a worker → SKIPPED. Observation without a worker is not a verdict. With a worker: identify → bind → run → verdict.

Guards: `test_identity_hash`, `test_plan_lock_bind`, `test_purity_boundary`, `test_invariants`, `test_bones`, `test_committed_plan_matches_live_body`.

Do not “improve” the hash canon without re-taking every `plan.json`.

## 3. Queue

| Phase | Point | Done | Do not |
|---|---|---|---|
| C0 | README + `judge` alias | copy-paste green | overwrite `acid-engine` on PyPI |
| C1 | `receipt.json` | `judge --receipt`; no `proven_pure` | dashboard |
| C2 | GitHub Action + `locks/index.json` | workflow + index; body swap is not PASS | hosted SaaS |
| C3 | 5 tools in `examples/tools/` | `.py`+`.json`+`.plan.json`; index bones+tools | a “news” entity in the core |
| C4 | one hook | PreToolUse bind; deny on a foreign hash; pre ≠ PASS | both harnesses at once |
| C5 | lock registry in git | `locks --index`; check, not hosted | hosted evidence |
| C6 | receipt signature | `receipt --verify`; local Ed25519 | before C1–C2 are stable |
| C7 | API=CLI, one judge | without plan+iface not PASS | merging judges |

Do not start a second hook (Cursor / Copilot / MCP) until the CLI showcase and one Claude hook are green. Ready supervisor binaries — GitHub Release, not `cargo` on the caller’s machine.

0.2.x is the fail-closed gate. It is not a payment-stable lock for an evidence service.

## 4. Start

```bash
pip install -e ".[dev]"
python -m pytest tests -q
acid-judge lock --help
acid-judge judge --script examples/bones/n_plus_one.json --plan examples/bones/n_plus_one.plan.json --input '{"n": 3}'
```
