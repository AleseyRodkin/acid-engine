# Acid Judge — commercial plan

**Date:** 12.09.2026
Law is only [METHOD.md](METHOD.md). Do not reopen [PLAN.md](PLAN.md) (0.1 bones).
Base snapshot: `c72ea42`. If `worker.py` / `lock` / `--plan` are missing — get a current zip first.

The personal experiment is done. Next: a fail-closed gate of a tool body. STOL is not a stand.

## 1. What we sell

Product: **Acid Judge** — an independent execution-integrity primitive, not a control plane.
Phrase: verifies that the code approved for an AI agent is the code that actually executes.
Not a policy gate. Not an MCP gateway. Not a sandbox. Not SLSA. A neighbor of those layers, not a replacement.

ICP: teams where AI changes a local tool with blast radius (payments, refunds, production data). Not “everyone who has an agent”.

Four surfaces: CLI, library, one hook, receipt. [INTEROP.md](INTEROP.md).
APort / AGT / Copilot adapters — on the caller’s request, not in 0.2.

First buyer: **AI Platform / Developer Platform**. Then AppSec. Governance — after receipts/evidence, not first.

Niche: approved-to-executed verification of a Python-tool body.

Three commands are the only public contract: `lock`, `judge`, `receipt`.

MIT core. They pay later for **evidence** (who approved, what ran, PASS/FAIL/SKIPPED, signature), not for a hosted registry of lock files. Do not write prices in the README.

Tiers (mental, do not publish prices):

| Tier | What | Why |
|---|---|---|
| Open core (MIT) | `lock` / `judge` / `receipt`, CLI, supervisor, `locks/` in git | distribution and audit |
| Team | central evidence, alerts on FAIL, receipt history | first paid unit |
| Enterprise | incident evidence, SIEM export, SSO, SLA | Governance after Platform |

Never in this plan: SaaS-OS, self-hosting, profiles, markdown specs, `proven_pure`, a scaffold for any project, aggregator-as-product, competing with Pydantic, JS/WASM/a second language, STOL, SKIPPED→PASS, twenty adapters, prices in README, MCP as a second harness before the CLI showcase is closed, Copilot before a green Claude hook, a risk score.

## 2. Must not break

- Hash = declaration + body canon (`ast.unparse`, else bytecode). ArtifactRef is not identity.
- `plan.lock` before run. Mismatch → FAIL, do not run the body.
- No execution → not PASS. Not enough facts → SKIPPED. `bool ≠ int`. pure+effects → FAIL.
- CLI `run --script` without `--plan` → SKIPPED. The worker does not write PASS/FAIL.
- `judge_script` / Pipeline / Composite without a plan+iface pair → SKIPPED. Without `toolchain` → SKIPPED. Self-lock is not a verdict.
- Rust without a worker → SKIPPED. Observation without a worker is not a verdict. With a worker: identify → bind → run → verdict.

Guards: `test_identity_hash`, `test_plan_lock_bind`, `test_purity_boundary`, `test_invariants`, `test_bones`, `test_committed_plan_matches_live_body`.

Do not “improve” the hash canon without re-taking every `plan.json`.

## 3. Queue

| Phase | Point | Done | Do not |
|---|---|---|---|
| C0 | README + `judge` alias | `4b87f13` copy-paste green | PyPI rename, prices |
| C1 | `receipt.json` | `judge --receipt`; no `proven_pure` | dashboard |
| C2 | GitHub Action + `locks/index.json` | workflow + index; body swap is not PASS | hosted SaaS |
| C3 | 5 tools in `examples/tools/` | `.py`+`.json`+`.plan.json`; index bones+tools | a “news” entity in the core |
| C4 | one hook | PreToolUse bind; deny on a foreign hash; pre ≠ PASS | both harnesses at once |
| C5 | lock registry in git | `locks --index`; check, not hosted | Governance $40k |
| C6 | receipt signature | `receipt --verify`; local Ed25519 | before C1–C2 are stable |
| C7 | niche B/C, API=CLI, one judge | API=CLI: without plan+iface not PASS | niche B/C and merging judges |

CLI `judge --plan` checks `runtime_hashes` (`c72ea42`). Do not start a second hook (Cursor / Copilot / MCP) until the CLI showcase and one Claude hook are green. Ready supervisor binaries — GitHub Release, not `cargo` on the buyer’s machine; not a C phase in this file.

Start at C0. Not with the Action, not with the hook, not with the signature. Do not start C(n+1) until Cn is green.

## 4. Start

```bash
PYTHONPATH=. python -m pytest tests -q
PYTHONPATH=. python -m acid_engine lock --help
PYTHONPATH=. python -m acid_engine run --script examples/bones/n_plus_one.json --plan examples/bones/n_plus_one.plan.json --input '{"n": 3}'
```
